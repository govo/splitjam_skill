# Projects and tracks

## How a project reference resolves

`--project` (or the positional) is tried in this order:

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
**equality**. So `stem:Lead Guitar`, `lead-guitar` and `LEADGUITAR` all resolve to `.leadGuitar`.

There is **no alias table and no fuzzy prefix matching**. When nothing matches, `hint` lists
every valid name — copy one from there instead of inventing an abbreviation.

`solo` affects exactly one track; there is no multi-select. "Drums and bass only" means
`solo stem:drums` plus `mute` on everything else.

## Mixer fields

| Command | Stored in | Semantics |
| --- | --- | --- |
| `track gain` | `PlaybackSettings.stemGains` / per-track field | linear 0...2; the free tier clamps to 1.0 and returns `W_CLAMPED` |
| `track pan` | `PlaybackSettings.stemPans` | −1 hard left … +1 hard right; **persisted**, survives reopening |
| `track mute` | per-track `isMuted` | actually silent |
| `track solo` | per-track `isSoloed` | solo |
| `track fold` | folded set in `PlaybackSettings` | **hides the lane only**, does not mute. Say this when the user says "hide" |
| `track extension` | extension stem visibility | show/hide refined stems, Pro |
| `track move` | user track order | place after another track |

`gain` and `speed` **clamp** (write succeeds with a warning); `pitch` and the section count
**refuse** (the whole call fails). Report the difference: clamping means "lower than requested,
but applied"; refusing means "nothing changed".

## Reading audio

- `track audio file` reports the path and format only, never the bytes;
- `track audio peaks --buckets N` returns a 0...1 normalised array for drawing waveforms;
- `track audio slice --range a-b` writes a real WAV to `--out` (default under `exports/`),
  at most 300 seconds per call, `--mono` to fold down. Do **not** decode audio in the skill —
  this is the only supported way to get samples out.
