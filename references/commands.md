# Command reference

Generated from `splitjam docs --json` (CLI 0.1.0). **Do not edit by hand** —
run `scripts/gen-commands.sh` after changing the CLI command table.

Every command also accepts the global flags: `--json`, `--project`, `--expect-revision`,
`--dry-run`, `--yes`, `--strict`, `--no-app-prompt`, `--timeout`, `--wait-startup`,
`--bridge-dir`. Flags may appear before or after the command.

## Diagnostics

| Command | Description | Parameters |
| --- | --- | --- |
| `splitjam ping` | Round-trip check to the running app. | — |
| `splitjam version` | App version and bridge schema. | — |
| `splitjam capabilities` | List operations with entitlement requirements. | — |
| `splitjam schema` | Protocol, error codes and exit codes. | — |

## Entitlement

| Command | Description | Parameters |
| --- | --- | --- |
| `splitjam entitlement get` | Entitlement snapshot (no network). | — |
| `splitjam entitlement refresh` | Refresh purchase state, then report. | — |
| `splitjam entitlement restore` | Restore purchases (app must be in front). | — |

## Projects

| Command | Description | Parameters |
| --- | --- | --- |
| `splitjam project list` | List projects. | — |
| `splitjam project get [project]` | Project detail: tracks, beat, sections, chords. | `project` (string) |
| `splitjam project rename [project] --name <text>` | Rename a project. | `project` (string)<br>`--name` (string) |
| `splitjam project note [project] --text "..."` | Set the project note (empty clears). | `project` (string)<br>`--text` (string) |
| `splitjam project star [project] [--starred false]` | Star or unstar a project. | `project` (string)<br>`--starred` (bool) |

## Tracks

| Command | Description | Parameters |
| --- | --- | --- |
| `splitjam track list [project]` | All tracks of a project. | `project` (string) |
| `splitjam track get <track> [--project <id>]` | One track. | `track` (string) |
| `splitjam track gain <track> --value 1.4` | Linear gain 0...2 (free clamps to 1.0). | `track` (string)<br>`--value` (number) |
| `splitjam track pan <track> --value -0.3` | Pan -1 (left) ... 1 (right). | `track` (string)<br>`--value` (number) |
| `splitjam track mute <track> [--unmute]` | Mute or unmute a track. | `track` (string)<br>`--muted` (bool)<br>`--unmute` (bool) |
| `splitjam track solo <track> [--unsolo]` | Solo or unsolo a track. | `track` (string)<br>`--soloed` (bool)<br>`--unsolo` (bool) |
| `splitjam track fold <track>` | Hide the lane (does not mute). | `track` (string)<br>`--folded` (bool) |
| `splitjam track unfold <track>` | Show the lane again. | `track` (string) |
| `splitjam track move <track> --after <track>` | Move a track after another. | `track` (string)<br>`--after` (string) |
| `splitjam track extension <track> [--visible false]` | Show or hide a refined stem (Pro). | `track` (string)<br>`--visible` (bool) |
| `splitjam track audio file <track>` | Audio file path, format and duration. | `track` (string)<br>`--channel` (string) |
| `splitjam track audio peaks <track> [--buckets 800]` | Normalized peak buckets. | `track` (string)<br>`--buckets` (int)<br>`--channel` (string) |
| `splitjam track audio slice <track> --range 12-24 [--mono]` | Export a range as WAV (max 5 min). | `track` (string)<br>`--mono` (bool)<br>`--out` (string)<br>`--range` (string) |

## Mixer

| Command | Description | Parameters |
| --- | --- | --- |
| `splitjam mixer master-volume --value 0.8` | Master volume 0...1. | `--value` (number) |
| `splitjam mixer master-pan --value 0.2` | Master pan -1...1. | `--value` (number) |
| `splitjam mixer speed --value 0.8` | Speed 0.1...2.0 (free clamps to 0.75...1.0). | `--value` (number) |
| `splitjam mixer pitch --semitones -2` | Pitch shift (free: +-3 semitones, 2 changes / 30 min). | `--cents` (int)<br>`--semitones` (int) |

## Beat grid

| Command | Description | Parameters |
| --- | --- | --- |
| `splitjam beat get [--include-beats]` | Source / applied / render / metronome. | `--include-beats` (bool) |
| `splitjam beat mode --mode tap` | Switch tap / automatic. | `--mode` (string) |
| `splitjam beat bpm 92` | Set manual BPM (tap mode, 30...300). | `bpm` (number)<br>`--bpm` (number) |
| `splitjam beat meter --beats-per-bar 3` | Beats per bar 2...16. | `--beats-per-bar` (int) |
| `splitjam beat multiplier --value 0.5` | 0.5 / 1 / 2 (auto only). | `--value` (number) |
| `splitjam beat density --value 2` | Auto beat density (power of two). | `--value` (number) |
| `splitjam beat anchor set --at 0.35 \| splitjam beat anchor clear` | Set (auto snaps) or clear the downbeat anchor. | `state` (string)<br>`--at` (string)<br>`--clear` (bool) |
| `splitjam beat lines on\|off` | Beat Lines on/off (also changes scrub step). | `state` (string)<br>`--enabled` (bool) |
| `splitjam beat accent on\|off` | Downbeat accent on/off. | `state` (string)<br>`--enabled` (bool) |
| `splitjam beat snap on\|off` | Snap to measure on/off. | `state` (string)<br>`--enabled` (bool) |
| `splitjam beat reset --target correction` | Reset correction or manual grid. | `--target` (string) |

## Metronome

| Command | Description | Parameters |
| --- | --- | --- |
| `splitjam metronome set --enabled true --volume 0.6` | Metronome switch, volume, beats per measure. | `--beats-per-measure` (int)<br>`--enabled` (bool)<br>`--volume` (number) |
| `splitjam metronome first-beat --at 0.5` | First beat: seconds, current or auto. | `--at` (string) |

## Sections

| Command | Description | Parameters |
| --- | --- | --- |
| `splitjam section list` | Practice sections. | `project` (string) |
| `splitjam section create --start 72 --end 96 --title Chorus` | Create a section (free up to 3). | `--end` (number)<br>`--start` (number)<br>`--title` (string) |
| `splitjam section update <id> --title "Verse 2"` | Update a section. | `id` (string)<br>`--end` (number)<br>`--start` (number)<br>`--title` (string) |
| `splitjam section delete <id>` | Delete a section. | `id` (string) |
| `splitjam section lock <id> [--locked false] \| --all` | Lock or unlock sections. | `id` (string)<br>`--all` (bool)<br>`--locked` (bool) |
| `splitjam section activate <id>` | Use a section as the A/B loop. | `id` (string) |
| `splitjam section deactivate` | Clear the A/B loop. | — |

## Chords

| Command | Description | Parameters |
| --- | --- | --- |
| `splitjam chord get` | Chord segments, key and bar notes. | `project` (string) |
| `splitjam chord note set --bar 2 --text "Am"` | Set the note of a bar. | `--bar` (int)<br>`--text` (string) |
| `splitjam chord note delete <id>` | Delete a bar note. | `id` (string) |
| `splitjam chord key --root C --mode major \| --auto` | Set or auto the displayed key. | `--auto` (bool)<br>`--mode` (string)<br>`--root` (string) |
| `splitjam chord display [--degree false]` | Toggle degree spelling. | `--degree` (bool) |

## Lyrics

| Command | Description | Parameters |
| --- | --- | --- |
| `splitjam lyrics get --format lrc` | Lyrics as json, lrc or plain. | `project` (string)<br>`--format` (string) |

## Local commands (no bridge)

| Command | Description |
| --- | --- |
| `splitjam doctor` | Presence, bridge path, token state and entitlement. Exits 3 when the app is closed but still prints everything. |
| `splitjam docs [--json]` | This table, as text or JSON. |
| `splitjam --version` | CLI version only. |
