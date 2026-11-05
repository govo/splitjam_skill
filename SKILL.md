---
name: splitjam
description: Drive the running SplitJam / StemsPlayer app on macOS over its local MCP server — read projects, set per-track gain/pan/mute/solo/fold, retune the beat grid (mode, BPM, meter, multiplier, anchor, beat lines, accent, snap), control the metronome, manage practice sections, edit chord display and per-bar notes, read lyrics, and export waveform peaks or WAV slices. Use when the user asks to "set the BPM to 92", "put the downbeat at 0.35s", "mute the bass", "solo the drums", "pan the lead guitar left", "hide the guitar lane", "set the gain to 1.4", "make a chorus section from 1:12 to 1:36", "slow the whole song down", "shift the pitch down two semitones", "show me the drums waveform", "export 12 to 24 seconds", or "read the lyrics" in SplitJam. Requires SplitJam running with Settings → MCP Server on; this skill connects through its own scripts/mcp.py using the token from Settings, so no client MCP config is needed. This skill never launches the app and never polls.
metadata:
  version: "1.0.0"
  requires: SplitJam with the MCP server (schema 3, 54 tools)
---

# SplitJam over MCP

The app hosts a **Model Context Protocol server** on `127.0.0.1:48321/mcp` (Streamable
HTTP, JSON-RPC 2.0) and exposes **54 tools**. There is no CLI to install and no
intermediate binary: an agent that has this server in its config calls the tools directly.

Everything happens on this Mac. No network, no upload, no daemon, no TCC permission — the
server only listens on loopback, and access is decided by one bearer token.

**So the app must be running, with the server switched on.** When it is not, nothing
answers and the request never happens — retrying a thousand times changes nothing. That is
not a flaky failure, it is a missing precondition.

## 0. The hard rules

1. **Check the link before working.** One `ping` (or `project_list`) is enough. It proves the
   server answers, the token is accepted, and — with `project_list` — that the project you are
   about to touch actually exists.
2. **If the call cannot connect, stop.** Two cases, two answers:
   - `mcp.py` cannot reach the endpoint (connection refused) → the app is closed, or the
     server switch is off;
   - the handshake returns 401 → the token is stale or missing.

   Both are fixed in the app (**Settings → MCP Server**), by the user. Do **not** launch the
   app, do **not** poll, do **not** read the app's container instead. Say that nothing was
   modified.
3. **Never trust memory for capabilities or entitlements.** The tool list comes from
   `tools/list`; what an op needs comes from `capabilities`; whether the user has Pro comes
   from `entitlement_get`. Never describe "cannot read the purchase state" as "you need to
   pay".
4. **Never touch the app's data by hand.** There is exactly one way to change SplitJam's
   content: these tools. Do not read, edit, or delete files under
   `~/Library/Containers/…`, `~/Library/Application Support/…` or the app's exports folder;
   on macOS 15+ the OS blocks it anyway, and on some versions it does so silently. Route
   everything through tools.
5. **Never ask the user for Full Disk Access.** If something is blocked, the answer is a
   different tool, not a bigger permission.
6. **On `E_PRO_REQUIRED`, stop.** The app has already shown its own upgrade prompt. Do not
   retry the same call, and never dodge the limit — no lower tier, no splitting one
   multi-stem export into ten single-stem ones.

## 1. Connecting (and diagnosing a broken connection)

The app hosts the server; **this skill talks to it**. `scripts/mcp.py` is a ~500-line
stdlib-only client that does the handshake, keeps the session, and calls tools. Nothing goes
into a client config, no JSON to edit, no app restart.

Two values come from **SplitJam → Settings → MCP Server**:

| Value | Where | Shape |
| --- | --- | --- |
| endpoint | status row, **Copy** | `http://127.0.0.1:48321/mcp` |
| token | token row, **Copy** | 64 hex chars; sent as `Authorization: Bearer <token>` |

Store the token once — `mcp.py` looks in three places, first hit wins:

```bash
--token <token>              # one call only
$SPLITJAM_TOKEN              # this shell
~/.config/splitjam/token     # persistent, 0600 — use this by default
```

```bash
mkdir -p ~/.config/splitjam
printf %s '<token>' > ~/.config/splitjam/token && chmod 600 ~/.config/splitjam/token

./scripts/mcp.py doctor          # presence, app, protocol, permission, tools, one verdict
./scripts/mcp.py call project_list
```

`doctor` answers "which part is broken" without guesswork; `health`, `tools`, `call` and
`snapshot` are the other subcommands. If the user's client speaks MCP natively and they would
rather see typed tools in the sidebar, registering the same URL plus an
`Authorization: Bearer <token>` header also works — but it is optional, and this skill never
depends on it.

Common causes, in the order they actually happen:

| Symptom | Cause | Fix |
| --- | --- | --- |
| connection refused | app closed, or the server is off | open the app, keep it running, turn the switch on |
| 401 on every call | token stale (regenerated, or server toggled) | copy the current token again |
| server fails to start, card says the port is taken | a second SplitJam instance, or another process, holds 48321 | quit whatever holds the port, then toggle **MCP Server** off and on — the port is fixed, there is no port setting to change |
| tools listed but every write returns `E_FORBIDDEN` | permission tier is **Read only** | raise it in the card |

The port does **not** roll forward. 48321 is the only port; if it is taken the app reports the
failure instead of silently moving.

## 2. Arguments every tool shares

| Argument | Applies to | Effect |
| --- | --- | --- |
| `project` | almost all | target project; **omit it when the app has exactly one**. Accepts a UUID, a UUID prefix, an exact name, or a unique substring |
| `dryRun` | every writing tool | validate — entitlement, permission and revision checks all run, nothing is written; the result comes back with `"dryRun": true` |
| `expectRevision` | every writing tool | optimistic lock: fail with `E_CONFLICT_REVISION` if the project changed since the revision you read |
| `confirm` | `section_delete` | required in addition to the tier; deleting a section is irreversible |
| `strict` | `track_gain`, `mixer_speed` | refuse instead of clamping at the free-tier limit |
| `noAppPrompt` | any | do not raise the in-app upsell prompt. Undocumented on purpose: it is for agents that already explained the wall, not for hiding it |

There are no global flags, no exit codes and no `--json`: every tool returns the same JSON
envelope as its single text content. `--json` became the default, `--yes` became
`confirm`, `--dry-run` became `dryRun`, `--expect-revision` became `expectRevision`.

## 3. The loop: read → check → write → read back

Before writing, **read the current state** (`project_get`, `track_list`, `beat_get`,
`section_list`, `chord_get`). Take the revision from that read, then write, then read again
to confirm what actually landed. Never guess an id or a track name.

```
project_list            {}                                  → pick the project id
track_list              { project: "<id>" }                  → see gain / pan / mute / fold
track_pan               { project: "<id>", track: "Lead Guitar", value: -0.3,
                          expectRevision: "<rev>" }          → write
track_get               { project: "<id>", track: "Lead Guitar" }  → read back
```

When writing several times to the same project, carry the previous response's `revision`
into `expectRevision`. "Someone changed it between my read and my write" then surfaces as
`E_CONFLICT_REVISION` instead of silently overwriting the user's edit.

## 4. Intent → tool

Tool names are the operation ids with `.` replaced by `_`; some clients prefix them with the
server name (`mcp__splitjam__track_gain`). Arguments are shown as JSON.

| The user says | Call | Notes |
| --- | --- | --- |
| "set the BPM to 92" | `beat_get` → if `mode=automatic`: `beat_mode {mode:"tap"}` → `beat_bpm {bpm:92}` → `beat_get` | changing BPM in automatic mode is refused (`E_MODE`) |
| "put the downbeat at 0.35s" | `beat_get` → `beat_anchor {at:"0.35"}` | automatic mode snaps to the nearest beat and fails with `E_ANCHOR_FAR` if it is too far; tap mode places it freely and rebuilds downbeats |
| "3 beats per bar" | `beat_meter {beatsPerBar:3}` | 2…16 |
| "hide the guitar" | `track_fold {track:"stem:guitar"}` | **hides the lane, does not mute**; undo with `folded:false` |
| "mute the bass" / "unmute" | `track_mute {track:"stem:bass"}` / `{muted:false}` | |
| "drums only" | `track_solo {track:"stem:drums"}`; for "drums and bass", solo one and mute the rest | solo takes a single track — do not pretend otherwise |
| "pan the lead guitar 30% left" | `track_pan {track:"Lead Guitar", value:-0.3}` | persisted; survives reopening |
| "set the gain to 1.4" | `track_gain {track:"<track>", value:1.4}` | free tier clamps to 1.0 and returns a `W_CLAMPED` warning |
| "chorus from 1:12 to 1:36" | `section_create {start:72, end:96, title:"Chorus"}` | free tier allows 3 sections; the 4th is refused and raises the upgrade prompt |
| "slow the whole song to 0.8" | `mixer_speed {value:0.8}` | free tier clamps into 0.75…1.0 |
| "down two semitones" | `mixer_pitch {semitones:-2}` | free: ±3 semitones, 2 changes per 30 minutes |
| "show me the drums waveform" | `track_audio_peaks {track:"stem:drums", buckets:800}` | |
| "export 12 to 24 seconds" | `track_audio_slice {track:"stem:drums", range:"12-24"}` | the app renders the WAV and returns it **as an audio content block** in the same result (≤8 MB; below that, one result carries both the envelope and the bytes) |
| "what are the chords" / "write Am on bar 2" | `chord_get` / `chord_note_set {bar:2, text:"Am"}` | the note is anchored to the **bar start in seconds**, not the bar number |
| "give me the lyrics" | `lyrics_get {format:"lrc"}` | read-only; `json` / `lrc` / `plain` |
| "which file is this track" | `track_audio_file {track:"<track>"}` | |
| "can I use high-precision separation" | `entitlement_get` → `stem_split_pro.allowed` | if not, say it is Pro-only and name the free tiers |
| "how many separations left" | `entitlement_get` → `weekly_separation_limit` | report remaining + `resets_at` |
| "what can you do" | `capabilities` | op list with `requires`, `constraint`, `permission`, `allowed` — cheaper and more accurate than guessing |

### Project and track references

**Project**: full UUID → UUID prefix → exact name → unique substring. Omit it when only one
project exists. Ambiguity returns candidates (`E_INVALID_ARG` with a hint) instead of picking
one — writing to the wrong project costs more than one extra call.

**Track**: `stem:drums` or the track name, case-insensitive and tolerant of spaces, hyphens
and underscores (`lead-guitar`, `LeadGuitar`, `stem:Lead Guitar` all resolve the same way).
Only the fixed `Stem` names resolve; `stem:guit` is not a prefix match and returns the list
of valid names. The recording track is read-only.

## 5. What to say when blocked

Every tool returns the same envelope — `{ ok, requestId, result, error, warnings, revision,
schemaVersion }` — and a business failure arrives with `isError: true` (not as a JSON-RPC
error, so the code is always visible). Branch on `error.code`:

| Situation | What to say |
| --- | --- |
| nothing answers / connection refused | "SplitJam is **not running** (nothing is listening on 127.0.0.1:48321), so I cannot operate it. Open the app, turn on **Settings → MCP Server**, and I will retry — nothing was modified." **Never say "I will open it for you"** |
| `401` on the handshake | "The MCP server rejected the token. Copy the current token from **Settings → MCP Server** again (regenerating it invalidates the old one), update `~/.config/splitjam/token`, then retry. Nothing was modified." |
| `E_SCHEMA` | "This client and the app speak different automation schemas. Update whichever is older, then retry. Nothing was modified." |
| `E_FORBIDDEN` | "SplitJam's permission is too narrow for this call — **Read only** blocks every write, and deleting needs **Edit + delete**. Ask the user to raise Permission in **Settings → MCP Server**. This is not a paywall: do not suggest upgrading, and nothing was modified." |
| `E_PRO_REQUIRED` + `reason=entitlement` | "This (high-precision separation / multi-stem export / a 4th section) is a Pro feature and this account has no Pro entitlement. The app has already shown its upgrade prompt. **Do not quote prices, do not push, do not buy for them.**" |
| `E_PRO_REQUIRED` + `reason=quota` | "The free quota is used up (3 separations per 7 days / 3 sections / 3 slices per hour). Next available at X, or Pro lifts the limit." |
| `E_ENTITLEMENT_UNKNOWN` | "**The purchase state for this account could not be read** (offline or the store service unavailable), so this cannot run. **That does not mean you have to pay.** Retry after `entitlement_refresh`." |
| `E_CONFLICT_REVISION` | Report the current revision, re-read with `project_get`, then write again. Do not blindly replay the same call. |
| `E_APP_NOT_FOREGROUND` | Only `entitlement_restore` needs the app in front. Ask the user to bring it forward, then retry. |
| `E_BUSY` / `E_CANCELLED` / `E_MODEL_MISSING` / `E_NO_BEAT_GRID` | Translate honestly and name the in-app action that fixes it. |

## 6. How to report back

Four lines are enough:

```
done       set "Lead Guitar" pan to -0.3 (30% left)
project    Midnight Drive (a1b2c3d4)
state      revision 7f3a91c2 · written to disk, still there after reopening
undo       track_pan { track: "Lead Guitar", value: 0 }
```

Undo is the inverse call, quoted so the user can run it themselves. Do not paste large JSON
blobs at the user — the envelope is for you, the four lines are for them. If a warning came
back (`W_CLAMPED`), the report must carry both numbers: "you asked for 1.4, the free tier
caps at 1.0, 1.0 was written".

## 7. Not supported in this version

These exist in the catalog as `implemented: false`, so they are **not exposed as tools**.
Say so instead of improvising:

- separation and import — do it in the app
- lyrics search, import, offset (`lyrics_get` is read-only)
- chord recognition — only the in-app button triggers it
- user track creation, nested tracks, asset replacement
- stem/mix export, audio-to-MIDI, staff/tab scores
- playback transport (play / pause / seek) and recording capture
- beat re-analysis — the in-app analysis button only

`capabilities` is the authority: anything not in `tools/list` cannot be called.

## 8. References

- `references/tools.md` — all 54 tools grouped by category, with parameters
- `references/contracts.md` — transport, auth, permission tiers, envelopes, error codes, warnings, revisions
- `references/tracks.md` — reference resolution, gain clamping, fold vs mute
- `references/beats.md` — the four beat layers and the three traps
- `references/lyrics.md` — the three `lyrics_get` formats
- `references/recipes.md` — copy-paste playbooks (retime a song, cut sections, start from scratch)
- `scripts/doctor.sh` — one-shot health check translated into plain language
- `scripts/snapshot.sh` — save a JSON snapshot of a project before changing it
- `scripts/gen-tools.sh` — regenerate `references/tools.md` from a running app
- `scripts/mcp.py` — the caller behind those three; `health` / `tools` / `call` / `snapshot`
