# Lyrics (read-only)

```bash
splitjam lyrics get [project] --format json|lrc|plain
```

| Format | Returns | Use |
| --- | --- | --- |
| `json` (default) | `{ "format": "json", "lyrics": { ... } }` — the whole `Lyrics` model | programmatic work: lines, timestamps, metadata |
| `lrc` | `{ "format": "lrc", "text": "..." }` | metadata tags `[ti:]/[ar:]/[al:]/[by:]/[offset:]` plus `[mm:ss.xx] line`. Saves straight to `.lrc` |
| `plain` | `{ "format": "plain", "text": "..." }` | plain lines, no timestamps |

A project without lyrics returns `E_NOT_FOUND`, with a hint pointing at the app's lyrics panel.

## What this version does not do

- **search** (`lyrics search`), **import** (`lyrics import --from-search`) and **global offset**
  (`lyrics offset`) are not implemented. If the user wants lyrics filled in, they do it in the
  app.
- Lyric fetching is performed by the app (zero network); the CLI does not talk to any lyrics
  source. That is a security boundary, not an omission.

## Before reading lyrics

`metadata.offset` is **global**. When the user complains that lyrics are half a beat late, read
the current offset out of the `json` format, then explain that changing it happens in the app —
do not try to synthesise an offset in the CLI.
