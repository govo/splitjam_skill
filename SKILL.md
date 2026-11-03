---
name: splitjam
description: Drive the running SplitJam / StemsPlayer app on macOS with the local `splitjam` CLI — read projects, set per-track gain/pan/mute/solo/fold, retune the beat grid (mode, BPM, meter, multiplier, anchor, beat lines, accent, snap), control the metronome, manage practice sections, edit chord display and per-bar notes, read lyrics, and export waveform peaks or WAV slices. Use when the user asks to "set the BPM to 92", "put the downbeat at 0.35s", "mute the bass", "solo the drums", "pan the lead guitar left", "hide the guitar lane", "set the gain to 1.4", "make a chorus section from 1:12 to 1:36", "slow the whole song down", "shift the pitch down two semitones", "show me the drums waveform", "export 12 to 24 seconds", "read the lyrics", or otherwise operate SplitJam from the terminal. Requires SplitJam to be running; this skill never launches the app, never polls, and never writes into the bridge directory by hand.
metadata:
  version: "0.1.0"
  requires: splitjam 0.1.0+
compatibility: macOS 13+ with SplitJam.app running, and `splitjam` on PATH (brew tap govo/tap && brew trust govo/tap && brew install splitjam). SplitJam → Settings → Command Line Access must be on.
allowed-tools: Bash(splitjam:*) Bash(${CLAUDE_SKILL_DIR}/scripts/*)
---

# SplitJam CLI

`splitjam` is a client for a **local file mailbox**: it writes a request into `inbox/` inside
the app's group container, the running app claims it, executes it, and writes the reply to
`outbox/`. No network, no ports, no daemon.

**So the app must be running.** When it is not, the request is never written — retrying a
thousand times changes nothing. That is not a flaky failure, it is a missing precondition.

## 0. Three hard rules

1. **Run `doctor` first.** Every task, every session.
2. **On `E_APP_NOT_RUNNING` / `E_APP_NOT_READY`, stop.** The only advice is "open SplitJam and
   keep it running (the window may be minimized, but do not quit), then retry". Do **not**
   launch the app yourself, do **not** poll, do **not** hand-write a request into the bridge
   directory. Say that nothing was modified.
3. **Never trust memory for capabilities or entitlements.** Capabilities come from
   `capabilities --json`, entitlement from `entitlement get`. Never describe "cannot read the
   purchase state" as "you need to pay".
4. **Never edit the app's data by hand.** There is exactly one way to change SplitJam's
   content — through the `splitjam` CLI. Do **not** read, edit, rename, or delete files in the
   app's group container, `~/Library/Containers/…`, `~/Library/Application Support/…`, or the
   bridge directory (`inbox/` / `working/` / `outbox/`), and do not write requests into the
   mailbox by hand. Editing app data directly can corrupt state and defeats every guard above;
   route everything through the CLI's commands and flags instead.

## 1. Getting started

```bash
splitjam doctor                      # presence, token, entitlement — works with the app closed
splitjam ping                        # one round trip
splitjam project list                # omit --project when only one project exists
splitjam capabilities --json         # every command with requires / constraint / mutates
```

## 2. Global flags

| Flag | Effect |
| --- | --- |
| `--json` | machine-readable envelope. **Always pass it** (works for `doctor` too) |
| `--project <id\|name>` | target project; optional when there is only one. Accepts an id prefix |
| `--expect-revision <r>` | optimistic lock: fail if the project changed since revision `r` (exit 5) |
| `--dry-run` | validate and report, write nothing |
| `--yes` | confirm a destructive operation (`section delete`) |
| `--strict` | reject instead of clamping at the free-tier limit |
| `--no-app-prompt` | do not raise the in-app upsell prompt |
| `--timeout <s>` | bridge timeout, default 15 |
| `--wait-startup <s>` | wait for a starting app, default 15, max 60 |
| `--bridge-dir <path>` | override the bridge directory |

Flags may appear before or after the command.

Exit codes: `0` ok · `2` argument · `3` app not running/ready · `4` not found · `5` conflict ·
`6` entitlement · `7` timeout · `8` schema · `9` internal. Details in
`references/contracts.md`.

## 3. The loop: read → check → write → read back

Before writing, **read the current state** (`track list`, `beat get`, `section list`,
`chord get`). Take the revision from that read, then write, then read again to confirm what
actually landed. Never guess an id or a track name.

```bash
# 1 read
splitjam --json project list
splitjam --json track list --project <id>
# 2 write, guarded by the revision you just read
splitjam --json track pan "Lead Guitar" --value -0.3 --project <id> --expect-revision <rev>
# 3 read back
splitjam --json track get "Lead Guitar" --project <id>
```

When writing several times to the same project, carry the previous response's `revision` into
`--expect-revision`. "Someone changed it between my read and my write" then surfaces as exit
code 5 instead of silently overwriting the user's edit.

## 4. Intent → commands

| The user says | Command chain | Notes |
| --- | --- | --- |
| "set the BPM to 92" | `beat get` → if `mode=automatic`: `beat mode --mode tap` → `beat bpm 92` → `beat get` | Changing BPM in automatic mode is refused (exit 2) |
| "put the downbeat at 0.35s" | `beat get` → `beat anchor set --at 0.35` | Automatic mode snaps to the nearest beat and fails with `E_ANCHOR_FAR` if it is too far; tap mode places it freely and rebuilds downbeats |
| "3 beats per bar" | `beat meter --beats-per-bar 3` | 2...16 |
| "hide the guitar" | `track fold stem:guitar` | **Hides the lane, does not mute.** Undo with `track unfold` |
| "mute the bass" / "unmute" | `track mute stem:bass` / `track mute stem:bass --unmute` | |
| "drums only" | `track solo stem:drums`; for "drums and bass", solo one and `track mute` the rest | Solo takes a single track — do not pretend otherwise |
| "pan the lead guitar 30% left" | `track pan "Lead Guitar" --value -0.3` | Persisted; survives reopening the project |
| "set the gain to 1.4" | `track gain <track> --value 1.4` | Free tier clamps to 1.0 and returns a `W_CLAMPED` warning |
| "chorus from 1:12 to 1:36" | `section create --start 72 --end 96 --title Chorus` | Free tier allows 3 sections; the 4th is refused and raises the upgrade prompt |
| "slow the whole song to 0.8" | `mixer speed --value 0.8` | Free tier clamps into 0.75...1.0 |
| "down two semitones" | `mixer pitch --semitones -2` | Free tier: ±3 semitones, 2 changes per 30 minutes |
| "show me the drums waveform" | `track audio peaks stem:drums --buckets 800` | |
| "export 12 to 24 seconds" | `track audio slice stem:drums --range 12-24` | WAV, ≤300s, add `--mono` for mono |
| "what are the chords" / "write Am on bar 2" | `chord get` / `chord note set --bar 2 --text Am` | The note is anchored to the **bar start in seconds**, not the bar number |
| "give me the lyrics" | `lyrics get --format lrc` | Read-only; `json` / `lrc` / `plain` |
| "which file is this track" | `track audio file <track> --channel original` | |
| "can I use high-precision separation" | `entitlement get` → `stem_split_pro.allowed` | If not, say it is Pro-only and name the free tiers |
| "how many separations left" | `entitlement get` → `weekly_separation_limit` | Report remaining + resets_at |

### Project and track references

**Project**: full UUID → UUID prefix → exact name → substring, in that order. Omit it when
only one project exists. Ambiguity lists candidates (exit 2) instead of picking one — writing
to the wrong project costs more than one extra command.

**Track**: `stem:drums` or the track name, case-insensitive and tolerant of spaces, hyphens and
underscores (`lead-guitar`, `LeadGuitar`, `stem:Lead Guitar` are the same track). Only the
fixed `Stem` names resolve — `stem:guit` is not a prefix match, it returns the list of valid
names. The recording track is read-only.

## 5. What to say when blocked

| Situation | What to say |
| --- | --- |
| `E_APP_NOT_RUNNING` | "SplitJam is **not running**, so I cannot operate it. Open the app (leave the window) and I will retry — nothing was modified." Include `lastSeen` ("it quit at 15:12"). **Never say "I will open it for you"** |
| `E_APP_NOT_READY` | "The app is running but not responding (probably busy). Bring it to the front and I will retry." |
| `E_AUTH` / missing token | "Settings → Command Line Access is off in the app; it needs to be turned on and authorized first." |
| `E_PRO_REQUIRED` + `reason=entitlement` | "This (high-precision separation / multi-stem export / a 4th section) is a Pro feature and this account has no Pro entitlement. The app has already shown its upgrade prompt. **Do not quote prices, do not push, do not buy for them.**" |
| `E_PRO_REQUIRED` + `reason=quota` | "The free quota is used up (3 separations per 7 days / 3 sections / 3 slices per hour). Next available at X, or Pro lifts the limit." |
| `E_ENTITLEMENT_UNKNOWN` | "**The purchase state for this account could not be read** (offline or the store service is unavailable), so this cannot run. **That does not mean you have to pay.** Retry after `entitlement refresh`." |
| `E_CONFLICT_REVISION` | Report the current revision, re-read with `project get`, then write again. Do not blindly replay the same request. |

**On `E_PRO_REQUIRED`, stop. Do not retry the same operation.** Never try to get around it by
changing parameters — dropping to a lower tier, or splitting one multi-stem export into ten
single-stem exports. That is circumventing the paywall, not finishing the task.

## 6. How to report back

Four lines are enough:

```
done       set "Lead Guitar" pan to -0.3 (30% left)
project    Midnight Drive (a1b2c3d4)
state      revision 7f3a91c2 · written to disk, still there after reopening
undo       splitjam track pan "Lead Guitar" --value 0
```

Do not paste large JSON blobs at the user. `--json` is for programs; the human gets the four
lines above.

## 7. Not supported in this version

These exist in the design but are **not implemented**. Say so instead of improvising:

- separation and import (`import`, `job`) — do it in the app
- lyrics search, import, offset (`lyrics` is read-only here)
- chord recognition (`chord recognize`) — only the in-app button triggers it
- user tracks, nested tracks, asset replacement
- stem export, audio-to-MIDI, staff/tab scores (`bundle` / `transcribe` / `score`)
- playback transport (play / pause / seek) and recording capture

The authority is always `splitjam capabilities --json`: entries with `implemented: false` are
refused before execution with `E_UNSUPPORTED`.

## 8. References

- `references/commands.md` — full command table with parameter types (generated)
- `references/contracts.md` — request/response envelopes, error codes, exit codes, `W_CLAMPED`
- `references/tracks.md` — reference resolution, gain clamping, fold vs mute
- `references/beats.md` — the four beat layers (source / applied / render / metronome)
- `references/lyrics.md` — the three `lyrics get` formats and LRC fields
- `references/recipes.md` — copy-paste playbooks (retime a song, cut sections, start from scratch)
- `scripts/doctor.sh` — one-shot health check translated into plain language
- `scripts/snapshot.sh` — save a JSON snapshot of a project before changing it
- `scripts/gen-commands.sh` — regenerate `references/commands.md` from the CLI's own table
