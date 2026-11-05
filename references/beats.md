# Beat grid: four layers

The beat grid is the easiest part of this surface to get wrong. **"Downbeat" is not
writable data; it is a render/audible switch.** `beat_get` reports four layers separately so
a switch never looks like a data change.

```
source          automatic analysis or manual tapping
   ↓ multiplier + correction (beatsPerBar / downbeatAnchorTime)
applied         the bpm, beats, downbeat candidates and measure lines actually in force
   ↓ render and audible switches
render          beatLines / accent / density / snapToMeasure
metronome       enabled / volume / firstBeatTime / beatsPerMeasure
```

## Which tool touches which layer

| Tool | Layer | Constraint |
| --- | --- | --- |
| `beat_mode { mode: "tap" \| "automatic" }` | selects the source | switching to tap builds a uniform grid from the current BPM if no manual grid exists |
| `beat_bpm { bpm }` | manual source | **tap mode only**; 30…300; automatic mode returns `E_MODE` |
| `beat_meter { beatsPerBar }` | correction | 2…16, changes how measures are divided |
| `beat_multiplier { value }` | applied tempo multiplier | automatic only; 0.5 / 1 / 2 |
| `beat_density { value }` | render | auto beat density, normalized to a power of two |
| `beat_anchor { at }` | correction | automatic mode **snaps** to the nearest beat; tap mode places it freely and rebuilds downbeats |
| `beat_anchor { clear: true }` | correction | removes the anchor |
| `beat_lines { enabled }` | render | also changes the scrub step and the ruler mode |
| `beat_accent { enabled }` | render | **only changes track line thickness**, never the data |
| `beat_snap { enabled }` | render | snap to measure |
| `beat_reset { target: "correction" \| "manual" }` | reset | `correction` clears meter and anchor; `manual` clears the tapped grid and returns to automatic |

## Three traps

**1. Changing BPM in automatic mode always fails.** Call `beat_mode { mode: "tap" }` first.
The order is `mode` → `bpm` → `anchor`; doing it backwards silently blocks the BPM write.

**2. Anchor snapping refuses rather than placing.** Automatic mode requires the anchor to be
within `max(0.08s, min(0.35s, median beat interval × 0.35))` of a beat. Outside that you get
`E_ANCHOR_FAR` and **nothing is written**. Either pass a time closer to a beat, or switch to
tap mode.

**3. `rulerUsesDownbeats` is always `true`.** With accent off, track lines become evenly
weighted, but the ruler and the "bar.beat" readout still follow downbeats. That is an
existing inconsistency in the app, not a broken switch — `beat_get` says so in
`render.note`. Do not try to "fix" it from here.

## A typical retime

```
beat_get        { project: "<id>" }                       → look at mode and grid first
beat_mode       { project: "<id>", mode: "tap" }
beat_bpm        { project: "<id>", bpm: 92 }
beat_anchor     { project: "<id>", at: "0.35" }
beat_get        { project: "<id>" }                        → verify applied.bpm == 92
```

`at` accepts a number as a string or a number, and `"current"` when the project is open in
the player. Do not pass the string `"auto"` to `beat_anchor`: auto is a mode, not a value.

## Metronome

Two tools, deliberately separate from the grid:

```
metronome_set        { project: "<id>", enabled: true, volume: 0.6, beatsPerMeasure: 4 }
metronome_firstBeat  { project: "<id>", at: "0.5" }     // or "current" / "auto"
```

`metronome_firstBeat` is not the downbeat anchor. Changing the grid does not move the
metronome's first beat, and vice versa — say which one you changed.

## Not available: `beat_analyze`

Re-running automatic analysis depends on the player's live audio session (`isSeparated`
plus an async analysis pass), which is not reliable headless. The app therefore does **not**
expose `beat.analyze` as a tool, and no error hint points at it. If the grid needs a re-run,
ask the user to do it in the app.
