# Tool reference

All 54 tools the app exposes over MCP. Mirrors `tools/list` — run
`SPLITJAM_TOKEN=<token> ./scripts/gen-tools.sh` against a running app to regenerate and
diff.

Tool name = operation id with `.` replaced by `_` (`track.audio.slice` → `track_audio_slice`).
Some clients prefix them with the server name, e.g. `mcp__splitjam__track_gain`.

**Every tool** also accepts:

| Argument | Meaning |
| --- | --- |
| `project` | target project; **omit when the app has exactly one**. UUID → prefix → exact name → unique substring |
| `dryRun` | writing tools only: run every check, write nothing, return `"dryRun": true` |
| `expectRevision` | writing tools only: fail with `E_CONFLICT_REVISION` if the project changed since that revision |
| `noAppPrompt` | suppress the in-app upsell prompt for this call (undocumented, for agents that already explained the wall) |

`?` marks optional parameters. Required ones have no marker. Parameters listed here are the
ones the app's own schema declares; extra keys are not rejected by the transport, so an
unknown parameter fails in the handler with `E_INVALID_ARG`, not at handshake time.

## Diagnostics

| Tool | What it does | Parameters |
| --- | --- | --- |
| `ping` | Round-trip health check (`pong`, `schemaVersion`, `pid`). | — |
| `version` | App version, schema version and transport. | — |
| `schema` | Full operation catalog including the parameters each op reads. | — |
| `capabilities` | Operation catalog with `requires`, `constraint`, `mutates`, `destructive`, `permission`, `allowed`, and the MCP `tool` name. | — |

## Entitlement

| Tool | What it does | Parameters |
| --- | --- | --- |
| `entitlement_get` | Current entitlement snapshot, no network. | — |
| `entitlement_refresh` | Refresh customer info, then return the snapshot. | — |
| `entitlement_restore` | Restore purchases. Needs the app in the foreground (`E_APP_NOT_FOREGROUND`). | — |

## Projects

| Tool | What it does | Parameters |
| --- | --- | --- |
| `project_list` | List projects with id, name, duration and revision. | — |
| `project_get` | Project metadata, tracks, beat, sections and chords. | `project?` |
| `project_rename` | Rename a project. | `project?`<br>`name` (string) |
| `project_note` | Set or clear the project note. | `project?`<br>`text` (string, `""` clears) |
| `project_star` | Star or unstar a project. | `project?`<br>`starred?` (bool, default `true`) |

## Tracks

| Tool | What it does | Parameters |
| --- | --- | --- |
| `track_list` | All tracks with gain, pan, mute, solo and fold state. | `project?` |
| `track_get` | One track by reference. | `project?`<br>`track` (string) |
| `track_gain` | Set linear gain 0…2 (not dB). | `project?`<br>`track`<br>`value` (number 0…2)<br>`strict?` (bool) |
| `track_pan` | Set stereo pan −1 (hard left) … 1 (hard right). | `project?`<br>`track`<br>`value` (number −1…1) |
| `track_mute` | Mute or unmute. | `project?`<br>`track`<br>`muted?` (bool, default `true`) |
| `track_solo` | Solo or unsolo one track. | `project?`<br>`track`<br>`soloed?` (bool, default `true`) |
| `track_fold` | Hide the lane on the timeline — **does not mute**. | `project?`<br>`track`<br>`folded?` (bool, default `true`) |
| `track_move` | Move a track after another; omit `after` to move it first. | `project?`<br>`track`<br>`after?` (string) |
| `track_extension` | Show or hide a refined extension stem (Pro). | `project?`<br>`track`<br>`visible?` (bool, default `true`) |

## Audio

| Tool | What it does | Parameters |
| --- | --- | --- |
| `track_audio_file` | Audio file path, format and duration. Path only, never the bytes. | `project?`<br>`track` |
| `track_audio_peaks` | Normalized 0…1 peak buckets for drawing a waveform. | `project?`<br>`track`<br>`buckets?` (int 8…20000, default 1000)<br>`channel?` (`both` \| `left` \| `right`) |
| `track_audio_slice` | Render a time range to WAV. Max 5 minutes per call. | `project?`<br>`track`<br>`range` (string `"12-24"`, seconds)<br>`mono?` (bool)<br>`out?` (file name) |

`track_audio_slice` returns the file **inline**, as an extra `audio` content block
(`audio/wav`, base64) in the same result as the JSON envelope. Above 8 MB the audio block is
replaced by a text note — request a shorter range instead of retrying. The envelope's `file`
and `path` point into the app's container, which is not readable from outside; use the
content block, not the path.

## Mixer

| Tool | What it does | Parameters |
| --- | --- | --- |
| `mixer_masterVolume` | Master volume 0…1. | `project?`<br>`value` (number 0…1) |
| `mixer_masterPan` | Master pan −1…1. | `project?`<br>`value` (number −1…1) |
| `mixer_speed` | Playback speed 0.1…2.0; free tier clamps into 0.75…1.0. | `project?`<br>`value` (number 0.1…2.0)<br>`strict?` (bool) |
| `mixer_pitch` | Pitch shift; free tier ±3 semitones, 2 changes per 30 min. | `project?`<br>`semitones?` (int −12…12)<br>`cents?` (int −100…100) |

`mixer_pitch` needs at least one of `semitones` / `cents`.

## Beat grid

| Tool | What it does | Parameters |
| --- | --- | --- |
| `beat_get` | Source / applied / render / metronome layers. | `project?`<br>`includeBeats?` (bool, large) |
| `beat_mode` | Switch tap / automatic grid source. | `project?`<br>`mode` (`tap` \| `automatic`) |
| `beat_bpm` | Manual BPM. **Tap mode only.** | `project?`<br>`bpm` (number 30…300) |
| `beat_meter` | Beats per bar. | `project?`<br>`beatsPerBar` (int 2…16) |
| `beat_multiplier` | Tempo multiplier. **Automatic mode only.** | `project?`<br>`value` (number, 0.5 / 1 / 2) |
| `beat_density` | Auto beat density; normalized to a power of two. | `project?`<br>`value` (number) |
| `beat_anchor` | Set (auto snaps) or clear the downbeat anchor. | `project?`<br>`at?` (seconds, or `"current"`)<br>`clear?` (bool) |
| `beat_lines` | Beat Lines on/off — also changes the scrub step and ruler mode. | `project?`<br>`enabled?` (bool) |
| `beat_accent` | Downbeat accent on/off — thickness only; rebuilds the beat track in automatic mode. | `project?`<br>`enabled?` (bool) |
| `beat_snap` | Snap to measure on/off, independent of Beat Lines. | `project?`<br>`enabled?` (bool) |
| `beat_reset` | Reset the grid. | `project?`<br>`target?` (`correction` \| `manual`, default `correction`) |

## Metronome

| Tool | What it does | Parameters |
| --- | --- | --- |
| `metronome_set` | Switch, volume, beats per measure. | `project?`<br>`enabled?` (bool)<br>`volume?` (number 0…1)<br>`beatsPerMeasure?` (int 2…16) |
| `metronome_firstBeat` | First beat position. | `project?`<br>`at` (seconds, `"current"`, `"auto"`) |

## Sections

| Tool | What it does | Parameters |
| --- | --- | --- |
| `section_list` | Practice sections of a project. | `project?` |
| `section_create` | Create a section (free tier: 3). | `project?`<br>`start` (number, seconds)<br>`end` (number, > start)<br>`title?` (string) |
| `section_update` | Change a range or a title. | `project?`<br>`id` (string, prefix ok)<br>`start?`<br>`end?`<br>`title?` |
| `section_delete` | Delete a section. Irreversible. | `project?`<br>`id`<br>`confirm?` (must be `true` unless `dryRun`) |
| `section_lock` | Lock or unlock. | `project?`<br>`id?`<br>`locked?` (bool, default `true`)<br>`all?` (bool) |
| `section_activate` | Use a section as the A/B loop. | `project?`<br>`id` |
| `section_deactivate` | Clear the A/B loop. | `project?` |

`section_delete` is destructive: it needs the **Edit + delete** tier **and** `confirm: true`.
Preview with `dryRun: true` first.

## Chords

| Tool | What it does | Parameters |
| --- | --- | --- |
| `chord_get` | Chord segments, key and per-bar notes. | `project?` |
| `chord_note_set` | Write the chord note of a bar. | `project?`<br>`bar` (int ≥ 1)<br>`text` (string) |
| `chord_note_delete` | Delete a bar note. Destructive. | `project?`<br>`id` (string, prefix ok) |
| `chord_key` | Set or auto the displayed key. | `project?`<br>`root?` (e.g. `"C#"`)<br>`mode?` (`major` \| `minor`)<br>`auto?` (bool) |
| `chord_display` | Show degrees instead of chord names. | `project?`<br>`degree?` (bool, default `true`) |

## Lyrics

| Tool | What it does | Parameters |
| --- | --- | --- |
| `lyrics_get` | Lyrics as `json`, `lrc` or `plain`. Read-only. | `project?`<br>`format?` (`json` \| `lrc` \| `plain`) |

## Annotation hints

`tools/list` also carries `annotations` per tool: `readOnlyHint` is true for everything with
no side effects, `destructiveHint` for `section_delete` and `chord_note_delete`,
`idempotentHint` mirrors `readOnlyHint`, `openWorldHint` is always false. Use them to decide
whether a `dryRun` pass is worth a round trip — for read-only tools it never is.
