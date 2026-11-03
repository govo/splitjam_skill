# Beat grid: four layers

The beat grid is the easiest part of this CLI to get wrong. **"Downbeat" is not writable data;
it is a render/audible switch.** `beat get` reports four layers separately so a switch never
looks like a data change.

```
source          automatic analysis or manual tapping
   ↓ multiplier + correction (beatsPerBar / downbeatAnchorTime)
applied         the bpm, beats, downbeat candidates and measure lines actually in force
   ↓ render and audible switches
render          beatLines / accent / density / snapToMeasure
metronome       enabled / volume / firstBeatTime / beatsPerMeasure
```

## Which command touches which layer

| Command | Layer | Constraint |
| --- | --- | --- |
| `beat mode --mode tap\|automatic` | selects the source | switching to tap builds a uniform grid from the current BPM if no manual grid exists |
| `beat bpm <n>` | manual source | **tap mode only**; 30...300; automatic mode returns `E_MODE` |
| `beat meter --beats-per-bar` | correction | 2...16, changes how measures are divided |
| `beat multiplier --value` | applied tempo multiplier | automatic only; 0.5 / 1 / 2 |
| `beat density --value` | render | auto beat density, powers of two |
| `beat anchor set --at <s>` | correction | automatic mode **snaps** to the nearest beat; tap mode places it freely and rebuilds downbeats |
| `beat anchor clear` | correction | removes the anchor |
| `beat lines on\|off` | render | also changes the scrub step |
| `beat accent on\|off` | render | **only changes track line thickness**, never the data |
| `beat snap on\|off` | render | snap to measure |
| `beat reset --target correction\|manual` | reset | `correction` clears meter and anchor; `manual` clears the tapped grid |

## Three traps

**1. Changing BPM in automatic mode always fails.** Run `beat mode --mode tap` first. The order
is `mode` → `bpm` → `anchor`; doing it backwards silently blocks the bpm write.

**2. Anchor snapping refuses rather than placing.** Automatic mode requires the anchor to be
within `max(0.08s, min(0.35s, median beat interval × 0.35))` of a beat. Outside that you get
`E_ANCHOR_FAR` and **nothing is written**. Either pass a time closer to a beat, or switch to
tap mode.

**3. `rulerUsesDownbeats` is always `true`.** With `accent` off, track lines become evenly
weighted, but the ruler and the "bar.beat" readout still follow downbeats. That is an existing
inconsistency in the app, not a broken switch — `beat get` says so in `render.note`.

## A typical retime

```bash
splitjam --json beat get                       # look at mode and grid first
splitjam --json beat mode --mode tap
splitjam --json beat bpm 92
splitjam --json beat anchor set --at 0.35
splitjam --json beat get                       # verify applied.bpm == 92
```

## Not available: `beat analyze`

Re-running automatic analysis depends on the player's live audio session (`isSeparated` plus an
async analysis pass), which is not reliable headless. The CLI therefore does **not** expose
`beat analyze`, and its error hints never point at that command. If the grid needs a re-run,
ask the user to do it in the app.
