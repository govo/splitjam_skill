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

## G. Find and import lyrics (including word-level timing)

```
project_list    {}                                            # 1 find the project id
lyrics_search   { project: "<id>", index: 0 }                 # 2 name becomes the query; index returns lyricsText
lyrics_import   { project: "<id>", text: "<lyricsText>",
                  dryRun: true }                              # 3 validate the parse, write nothing
lyrics_import   { project: "<id>", text: "<lyricsText>" }     # 4 write, keep the returned revision
lyrics_get      { project: "<id>", format: "json" }           # 5 read back lines, word timestamps, offsets
lyrics_offset   { project: "<id>", delta: -0.3,
                  expectRevision: "<rev>" }                   # 6 fine-tune against the recording
```

Notes:
- `lyrics_search` is the only tool here that uses the network; `E_LYRICS_SOURCE` means the
  upstream failed, not that the user must pay. Try another `source` or ask for the LRC text.
- Enhanced word-level LRC (`[00:30.10]<00:30.10>往<00:30.40>日…`) parses into the same
  `Lyrics` model as the in-app import sheet — no separate tool is needed for karaoke timing.
- Import **replaces** existing lyrics and resets the global offset unless `keepOffset: true`
  or an explicit `offset` is given. When overwriting, `dryRun` + `expectRevision` first.
- A search result may be for a different recording than the one in the project; when timings
  are globally off, adjust with `lyrics_offset { delta: … }`, not by rewriting every line.
