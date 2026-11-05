# Lyrics (read-only)

```
lyrics_get { project: "<id>", format: "json" | "lrc" | "plain" }
```

| Format | Returns | Use |
| --- | --- | --- |
| `json` (default) | `{ "format": "json", "lyrics": { … } }` — the whole `Lyrics` model | programmatic work: lines, timestamps, metadata |
| `lrc` | `{ "format": "lrc", "text": "…" }` | metadata tags `[ti:]/[ar:]/[al:]/[by:]/[offset:]` plus `[mm:ss.xx] line`. Saves straight to `.lrc` |
| `plain` | `{ "format": "plain", "text": "…" }` | plain lines, no timestamps |

`text` is accepted as an alias for `plain`; the canonical value is `plain`.

A project without lyrics returns `E_NOT_FOUND`, with a hint pointing at the app's lyrics
panel.

## What this does not do

- **search**, **import** and **global offset** are not implemented — the app never exposes
  them as tools. If the user wants lyrics filled in or shifted, they do it in the app.
- Lyric fetching is performed by the app (zero network); no tool talks to a lyrics source.
  That is a security boundary, not an omission.

## Before reading lyrics

`metadata.offset` is **global**. When the user complains that lyrics are half a beat late,
read the current offset out of the `json` format, then explain that changing it happens in
the app — do not try to synthesise an offset by re-reading with shifted timestamps.
