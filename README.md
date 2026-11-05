# splitjam-skill

Agent skill for **SplitJam** (StemsPlayer) on macOS. This repo **is** the skill — `SKILL.md`,
`references/` and `scripts/` live at the root, so it can be symlinked or copied straight into
`~/.workbuddy/skills/splitjam`.

The skill drives the running app through the `splitjam` CLI: read projects, set
gain/pan/mute/solo/fold, retune the beat grid, run the metronome, manage practice sections,
edit chords and bar notes, read lyrics, export waveform peaks and WAV slices.

Two companions:

- CLI binaries: [`govo/splitjam_cli`](https://github.com/govo/splitjam_cli) — `brew install govo/tap/splitjam`
- Homebrew tap: [`govo/homebrew-tap`](https://github.com/govo/homebrew-tap)

## Install

The repo root is the skill, so point the skill directory straight at this checkout.

### Symlink (development — edits take effect immediately)

```bash
ln -sfn "$PWD" ~/.workbuddy/skills/splitjam
```

### Copy

```bash
cp -R . ~/.workbuddy/skills/splitjam
```

Either way the skill shows up as `splitjam` in the skill settings.

## Structure

```
splitjam_skill/                 # the repo root is the skill
├── SKILL.md                    # the part read every session (hard rules, intents, reporting)
├── references/
│   ├── commands.md             # full command table — generated from `splitjam docs`, do not edit
│   ├── contracts.md            # envelopes, error codes, exit codes, W_CLAMPED
│   ├── tracks.md               # reference resolution, clamping, fold vs mute
│   ├── beats.md                # the four beat layers
│   ├── lyrics.md               # the three lyrics formats (read-only)
│   └── recipes.md              # copy-paste playbooks
└── scripts/
    ├── doctor.sh               # health check rendered as plain language
    ├── snapshot.sh             # JSON snapshot of a project before changing it
    └── gen-commands.sh         # regenerate references/commands.md
```

## Maintenance

**Do not hand-write the command table.** It is generated from the CLI's own registry:

```bash
./scripts/gen-commands.sh
# without splitjam installed:
SPLITJAM_BIN=../demucs/cli/.build/debug/splitjam ./scripts/gen-commands.sh
```

The data source is `splitjam docs --json`, so the reference cannot drift from the binary.

When editing `SKILL.md`, keep two rules:

1. Only what must be remembered goes in `SKILL.md`; details go to `references/`.
2. Every command named there must actually exist. This CLI has no `beat analyze`, no `import`,
   no `lyrics offset` and no `score` commands — do not write "just run `splitjam beat analyze`",
   because an agent will call it and burn turns on `unknown command`.

## Version

`SKILL.md`'s `metadata.version` tracks the CLI release (`requires:` states the floor). Current:
CLI 0.3.0, schema 2.

The floor matters: `doctor.sh` reads the port-discovery fields of `doctor --json` (`endpoint`,
`ports.splitjamInstances`, `presence: incompatible`) that only exist from 0.2.0 onward, and 0.3.0
is where the app reports a **permission tier** (`read` / `edit` / `own`) and refuses writes with
`E_FORBIDDEN` (exit 10). Against an older binary the agent would be told it can work while every
write fails.
