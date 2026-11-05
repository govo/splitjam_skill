# Projects and tracks

## How a project reference resolves

The `project` argument is tried in this order:

1. full UUID (case-insensitive)
2. UUID prefix (must be unique)
3. exact project name (case-insensitive)
4. name substring (must be unique)

Omitted: a single project is used; with several you get `E_INVALID_ARG` and the first five
candidates in `hint`. Ambiguity returns `E_INVALID_ARG` plus candidates — it never picks one
silently.

## How a track reference resolves

```swift
enum Stem: String { case drums = "Drums", bass = "Bass", other = "Other",
    vocals = "Vocals", guitar = "Guitar", piano = "Piano",
    leadGuitar = "Lead Guitar", rhythmGuitar = "Rhythm Guitar",
    acousticGuitar = "Acoustic Guitar", guitarOther = "Guitar Other",
    recording = "Recording", bowedStrings = "Bowed Strings", synth = "Synth",
    brass = "Brass", saxophone = "Saxophone", backVocal = "Back Vocal",
    remainingOther = "Remaining Other", leadVocal = "Lead Vocal" }
```

Matching: strip an optional `stem:` prefix → lowercase → remove spaces, `-` and `_` → require
**equality**. So `stem:Lead Guitar`, `lead-guitar` and `LEADGUITAR` all resolve to
`.leadGuitar`.

There is **no alias table and no fuzzy prefix matching**. When nothing matches, `hint` lists
every valid name — copy one from there instead of inventing an abbreviation.

`solo` affects exactly one track; there is no multi-select. "Drums and bass only" means
`solo` on drums plus `mute` on everything else.

## Mixer fields

| Tool | Stored in | Semantics |
| --- | --- | --- |
| `track_gain` | `PlaybackSettings.stemGains` / per-track field | linear 0…2; the free tier clamps to 1.0 and returns `W_CLAMPED` |
| `track_pan` | `PlaybackSettings.stemPans` | −1 hard left … +1 hard right; **persisted**, survives reopening |
| `track_mute` | per-track `isMuted` | actually silent |
| `track_solo` | per-track `isSoloed` | solo |
| `track_fold` | folded set in `PlaybackSettings` | **hides the lane only**, does not mute. Say this when the user says "hide" |
| `track_extension` | extension stem visibility | show/hide refined stems, Pro |
| `track_move` | user track order | place after another track (omit `after` to move it first) |

`gain` and `speed` **clamp** (write succeeds with a warning); `pitch` and the section count
**refuse** (the whole call fails). Report the difference: clamping means "lower than
requested, but applied"; refusing means "nothing changed".

Passing `strict: true` to `track_gain` / `mixer_speed` turns a clamp into a refusal, which is
what a script wants when a silently reduced value is worse than an error.

## Reading audio

- `track_audio_file` reports the path, format and duration only, never the bytes. The path is
  inside the app's container and is not readable from outside — useful as an identifier, not
  as a file handle.
- `track_audio_peaks` returns a 0…1 normalized array for drawing waveforms
  (`buckets` 8…20000, `channel` `both` / `left` / `right`).
- `track_audio_slice` renders a real WAV and returns it **as an audio content block** in the
  same result, at most 300 seconds per call, `mono: true` to fold down. Do **not** decode
  audio yourself — this is the only supported way to get samples out. Above 8 MB the block is
  replaced by a note; request a shorter range.
