# Playbooks

Each playbook is a complete chain, including the failure branches. Arguments are JSON as a
tool would receive them; `project` is omitted in a single-project setup.

## A. Build a practice version from scratch

Goal: 92 BPM, downbeat at 0.35 s, keep drums and bass, cut one chorus section.

```
ping                                                  # 1 precondition: server up, token ok
project_list          {}                              # 2 find the project id
project_get           { project: "<id>" }             # 3 tracks, and whether a grid exists

beat_get              { project: "<id>" }             # 4 check mode
beat_mode             { project: "<id>", mode: "tap" }
beat_bpm              { project: "<id>", bpm: 92 }
beat_anchor           { project: "<id>", at: "0.35" }
beat_get              { project: "<id>" }             # 5 verify applied.bpm

track_mute            { project: "<id>", track: "stem:guitar" }
track_mute            { project: "<id>", track: "stem:vocals" }
# mute the rest the same way; do not fake multi-solo

section_create        { project: "<id>", start: 72, end: 96, title: "Chorus" }
project_get           { project: "<id>" }             # 6 final revision for the report
```

Failure branches:
- step 4 shows `mode` already `tap` → skip the mode call;
- `beat_bpm` returns `E_MODE` → still in automatic mode, go back one step;
- `beat_anchor` returns `E_ANCHOR_FAR` → the time is too far from a beat; pick a closer one
  or stay in tap mode;
- `section_create` returns `E_PRO_REQUIRED` → **stop**, report per §5 of SKILL.md, never
  delete existing sections to make room.

## B. Cut several sections

```
beat_get        { project: "<id>" }                                   # bar length = 60/bpm*beatsPerBar
section_list    { project: "<id>" }                                   # how many are used (free tier: 3)
section_create  { project: "<id>", start: 72, end: 84, title: "Chorus 1", dryRun: true }
section_create  { project: "<id>", start: 72, end: 84, title: "Chorus 1" }
```

Always `dryRun` first. Overlapping sections are neither merged nor rejected — compute the
ranges yourself and mention any overlap in the report so the user is not surprised later.
Deleting is different: `section_delete` needs `confirm: true` **and** the Edit + delete tier.

## C. Mixer-only changes

```
track_list    { project: "<id>" }
track_pan     { project: "<id>", track: "Lead Guitar", value: -0.3 }
track_gain    { project: "<id>", track: "stem:drums", value: 1.4 }
track_get     { project: "<id>", track: "Lead Guitar" }
```

When `track_gain` returns `W_CLAMPED`, the report must carry both numbers: "you asked for
1.4, the free tier caps at 1.0, 1.0 was written". Never say "set to 1.4".

## D. Export a slice for an external tool

```
track_audio_file   { project: "<id>", track: "stem:drums" }               # does the asset exist
track_audio_peaks  { project: "<id>", track: "stem:drums", buckets: 800 }
track_audio_slice  { project: "<id>", track: "stem:drums", range: "12-24" }
```

At most 300 seconds per call, 8 MB inline. For a whole song, state the plan first ("N
slices, each X long"), then do it. The WAV arrives as an `audio` content block; `file` and
`path` in the envelope are names inside the app's container, not a path you can open.

## E. Handling a free-tier wall

```
entitlement_get   {}
# look at weekly_separation_limit / stem_split_pro / multi_stem_export / multiple_sections
section_create    { project: "<id>", start: 0, end: 10, title: "A" }
# if it returns E_PRO_REQUIRED
entitlement_get   {}          # confirm reason: entitlement or quota
```

Then do exactly one thing: state the conclusion and stop.

- `entitlement` → "this is a Pro feature, the app already showed its prompt, retry after
  upgrading"
- `quota` → "the free quota is used up, next available at X"

No retrying with different parameters, no splitting one operation into several to dodge a
limit, no pushing the upgrade.

## F. Revision conflict

```
track_pan    { project: "<id>", track: "stem:bass", value: 0.2, expectRevision: "7f3a91c2" }
# E_CONFLICT_REVISION; error.hint carries the current revision
project_get  { project: "<id>" }          # re-read and see what changed
# write again with the new revision
```

A conflict means someone changed the project after your read — usually the user, in the UI.
Do **not** drop `expectRevision` and write anyway; that overwrites their edit.

## G. "Find the lyrics" — one sentence, finished sheet

The user says "帮我找这首歌的歌词" / "identify the lyrics" / "I want word-by-word". No
questions back: the defaults below are the answer. Target output is **word-level** — from the
catalog when it has word tags, otherwise written by you from the vocal stem. Line-level is
what you report when no audio path exists at all, and you say why.

```text
ping                                                          # 0 server alive
project_list         {}                                       # 1 which project (omit project when one)
lyrics_get           { project: "<id>", format: "json" }      # 2 L0: wordCount > 0 → report, stop
lyrics_search        { project: "<id>", limit: 10 }           # 3 L1: name = query, duration = anchor
lyrics_search        { project: "<id>", index: 3 }            # 4 text + detectedFormat

# --- L2 / L3: no word tags anywhere, do the listening yourself ---
track_audio_file     { project: "<id>", track: "stem:vocals" }          # 5 the stem must exist
track_audio_slice    { project: "<id>", track: "stem:vocals",
                       range: "0-60", mono: true }                      # 6 WAV path printed on stdout
track_audio_peaks    { project: "<id>", track: "stem:vocals",
                       buckets: 9600 }                                  # 7 optional: snap onsets

lyrics_import        { project: "<id>", text: "<lrc>",
                       dryRun: true }                                   # 8 only when replacing
lyrics_import        { project: "<id>", text: "<lrc>" }                 # 9 write, keep revision
lyrics_get           { project: "<id>", format: "json" }                # 10 verify wordCount
lyrics_offset        { project: "<id>", delta: -0.4,
                       expectRevision: "<rev>" }                        # 11 only if timing is off
```

Decision table — already answered, do not ask:

| Fork | Take |
| --- | --- |
| project already has `wordCount > 0` | report it (`lines`, `words`, `offset`) and stop. Replace only on "redo / replace / another version" |
| project has line-level lyrics, user wants word-level | replacing is allowed — that is an upgrade, still `dryRun` first |
| project name is "Untitled" / "demo 3" | ask for **track + artist** once (the only unavoidable question), then search with those two fields |
| several results, same title | closest `duration` wins; ≤5 s off the project, skip `live` / `cover` / `remix` / `instrumental` |
| `detectedFormat: "lrc"` | one more pass: `source: "karalyr"`, then `index` on results 1–2. Still no word tags → **keep that text as the transcript** and time it from the stem (§4 of `lyrics.md`) |
| `detectedFormat: "plainText"` | no timing at all — usable as a transcript for L2, never imported as-is while a stem exists |
| no usable result (`E_LYRICS_SOURCE`, or nothing matches) | L3: transcribe the vocal stem yourself, then time it |
| the client cannot take audio blocks | L4: line-level, or hand-built timing if the user insists — and the report says which |
| `E_NOT_FOUND` from `track_audio_file` | the project was never separated; that happens in the app, no MCP call creates stems |
| `E_LYRICS_SOURCE` | read `statuses`, report network not paywall, retry once or switch `source`, or ask for the LRC text |
| user says "0.4s late" | `delta: -0.4` (words move earlier). One correction only |

Failure branches:
- `E_FORBIDDEN` → permission tier is Read only; the user raises it, nothing was written;
- `E_CONFLICT_REVISION` → `project_get`, then re-import with the fresh revision — do not drop
  `expectRevision` and write anyway;
- import returns `wordCount: 0` although the text had word tags → the tags were malformed
  (see `lyrics.md` §1: word standard needs ≥2 tags per line, enhanced needs `<mm:ss.xx>`),
  fix the text and re-import; do not report success.

Slicing budget for L2 / L3 — state it before you start on a long song:

```
duration 240s → 5 slices: 0-60, 58-118, 116-176, 174-234, 232-240
each call : mono: true · ~5.3 MB · printed as ~/.cache/splitjam/audio/<id>_vocals_<range>_mono.wav
merge     : absolute time = slice start + local time; drop the duplicated seam line
```

Never exceed 60 s or drop `mono` — 8 MiB of raw WAV is the inline cap, and an oversized slice
comes back as a text note instead of audio, which reads like a silent failure.

Exporting instead of importing:

```
lyrics_get { project: "<id>", format: "lrc" }   # sheet in its own format — word tags survive
```

Search results can belong to a different recording (live, remaster, different take). When the
whole sheet is uniformly off, adjust once with `lyrics_offset { delta: … }`; when the drift
grows through the song, the sheet is for another take — re-search by duration rather than
rewriting every line.
