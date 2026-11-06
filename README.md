# splitjam-skill

Agent skill for **SplitJam** (StemsPlayer) on macOS. This repo **is** the skill — `SKILL.md`,
`references/` and `scripts/` live at the root, so it can be symlinked or copied straight into
`~/.workbuddy/skills/splitjam`.

The skill drives the running app over its **local MCP server**: read projects, set
gain/pan/mute/solo/fold, retune the beat grid, run the metronome, manage practice sections,
edit chords and bar notes, search/read/import lyrics and shift their global offset, export
waveform peaks and WAV slices.

Its lyrics track is written as one chain, not four tools: "find the lyrics", "identify this
song's lyrics", "give me word-by-word", "歌词对不上" all run the same
search → pick the right recording → (catalog text, or transcribe the vocal stem yourself) →
time the words → import → verify → offset sequence. The app has no ASR on purpose — the agent
listens to `track_audio_slice` output and writes the lyrics back — and the output defaults to
word-level.

There is nothing else to install. The app hosts the server itself
(`http://127.0.0.1:48321/mcp`, 57 tools, Streamable HTTP) and the skill talks to it through
`scripts/mcp.py` — **no MCP client config to write, nothing to restart**. Registering the same
URL in a client that speaks MCP natively still works, but it is optional.

## Setup

1. In SplitJam: **Settings → MCP Server** → switch it on.
2. Copy the token from the same card.
3. Store it where `scripts/mcp.py` looks (`--token`, then `$SPLITJAM_TOKEN`, then this file):

```bash
mkdir -p ~/.config/splitjam
printf %s '<token>' > ~/.config/splitjam/token && chmod 600 ~/.config/splitjam/token
./scripts/mcp.py doctor
```

`doctor` names the cause when something is off (app closed, server off, stale token, read-only
tier) and the fix. A healthy one ends with `ok ready to work.`

## Install the skill

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
│   ├── tools.md                # all 57 tools with parameters — mirrors tools/list
│   ├── contracts.md            # transport, auth, permission tiers, envelopes, error codes
│   ├── tracks.md               # reference resolution, clamping, fold vs mute
│   ├── beats.md                # the four beat layers
│   ├── lyrics.md               # the whole lyrics chain: capability boundary, picking a result, word-level grammar, estimation, offsets
│   └── recipes.md              # copy-paste playbooks
└── scripts/
    ├── mcp.py                  # handshake + tools/call; audio slices land in ~/.cache/splitjam/audio
    ├── doctor.sh               # health check rendered as plain language
    ├── snapshot.sh             # JSON snapshot of a project before changing it
    └── gen-tools.sh            # regenerate references/tools.md from a running app
```

## Maintenance

**Do not hand-write the tool table.** It is derived from the app's single catalog, and the
same table is what `tools/list` returns:

```bash
./scripts/gen-tools.sh   # token from ~/.config/splitjam/token
```

When editing `SKILL.md`, keep two rules:

1. Only what must be remembered goes in `SKILL.md`; details go to `references/`.
2. Every tool named there must actually exist. The catalog now has `lyrics_search`,
   `lyrics_import` and `lyrics_offset`, but still no `beat_analyze`, no separation / audio
   import and no score tools — do not write "just call `beat_analyze`", because an agent will call it
   and burn turns on `E_UNSUPPORTED`.

## Version

`SKILL.md`'s `metadata.version` tracks the app's automation contract. Current: schema 3,
MCP protocol 2025-06-18, 57 tools, permission tiers `read` / `edit` / `own`.

The floor matters. `scripts/doctor.sh` reads `/health` fields (`protocolVersion`,
`schemaVersion`, `permission`, `toolCount`) that only exist on the MCP build, and the whole
skill assumes business errors arrive as `isError: true` tool results rather than process exit
codes. Against the older HTTP-service build every call here fails.
