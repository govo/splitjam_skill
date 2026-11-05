# splitjam-skill

Agent skill for **SplitJam** (StemsPlayer) on macOS. This repo **is** the skill — `SKILL.md`,
`references/` and `scripts/` live at the root, so it can be symlinked or copied straight into
`~/.workbuddy/skills/splitjam`.

The skill drives the running app over its **local MCP server**: read projects, set
gain/pan/mute/solo/fold, retune the beat grid, run the metronome, manage practice sections,
edit chords and bar notes, read lyrics, export waveform peaks and WAV slices.

There is nothing else to install. The app hosts the server itself
(`http://127.0.0.1:48321/mcp`, 54 tools, Streamable HTTP), so the only setup is registering
that endpoint in whatever MCP client the agent runs in.

## Setup

1. In SplitJam: **Settings → MCP Server** → switch it on.
2. Copy the endpoint and the token from the same card.
3. Add them to the agent's MCP config:

```json
{
  "mcpServers": {
    "splitjam": {
      "type": "http",
      "url": "http://127.0.0.1:48321/mcp",
      "headers": { "Authorization": "Bearer <token>" }
    }
  }
}
```

If the connection does not work, run `SPLITJAM_TOKEN=<token> ./scripts/doctor.sh` — it names
the cause (app closed, server off, stale token, read-only tier) and the fix.

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
│   ├── tools.md                # all 54 tools with parameters — mirrors tools/list
│   ├── contracts.md            # transport, auth, permission tiers, envelopes, error codes
│   ├── tracks.md               # reference resolution, clamping, fold vs mute
│   ├── beats.md                # the four beat layers
│   ├── lyrics.md               # the three lyrics formats (read-only)
│   └── recipes.md              # copy-paste playbooks
└── scripts/
    ├── mcp.py                  # handshake + tools/call, no dependencies beyond python3
    ├── doctor.sh               # health check rendered as plain language
    ├── snapshot.sh             # JSON snapshot of a project before changing it
    └── gen-tools.sh            # regenerate references/tools.md from a running app
```

## Maintenance

**Do not hand-write the tool table.** It is derived from the app's single catalog, and the
same table is what `tools/list` returns:

```bash
SPLITJAM_TOKEN=<token> ./scripts/gen-tools.sh
```

When editing `SKILL.md`, keep two rules:

1. Only what must be remembered goes in `SKILL.md`; details go to `references/`.
2. Every tool named there must actually exist. The catalog has no `beat_analyze`, no import,
   no `lyrics_offset` and no score tools — do not write "just call `beat_analyze`", because an
   agent will call it and burn turns on `E_UNSUPPORTED`.

## Version

`SKILL.md`'s `metadata.version` tracks the app's automation contract. Current: schema 3,
MCP protocol 2025-06-18, 54 tools, permission tiers `read` / `edit` / `own`.

The floor matters. `scripts/doctor.sh` reads `/health` fields (`protocolVersion`,
`schemaVersion`, `permission`, `toolCount`) that only exist on the MCP build, and the whole
skill assumes business errors arrive as `isError: true` tool results rather than process exit
codes. Against the older HTTP-service build every call here fails.
