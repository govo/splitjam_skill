# Lyrics

Four tools: **search online → read → import → shift**. `lyrics_get` is read-only;
`lyrics_search` is read-only but uses the network; `lyrics_import` and `lyrics_offset` write to
the project and need the `edit` permission tier.

```
lyrics_search  { query: "...", track: "...", artist: "...", index: 0 }
lyrics_get     { project: "<id>", format: "json" | "lrc" | "plain" }
lyrics_import  { project: "<id>", text: "<lrc>", dryRun: true }
lyrics_offset  { project: "<id>", delta: 0.3, expectRevision: "<rev>" }
```

## 1. `lyrics_get` — read

| Format | Returns | Use |
| --- | --- | --- |
| `json` (default) | `{ "format": "json", "lyrics": { … } }` — the whole `Lyrics` model | programmatic work: lines, word timestamps, `metadata.offset`, `userOffset` |
| `lrc` | `{ "format": "lrc", "text": "…" }` | metadata tags `[ti:]/[ar:]/[al:]/[by:]/[offset:]` plus `[mm:ss.xx] line`. Saves straight to `.lrc` |
| `plain` | `{ "format": "plain", "text": "…" }` | plain lines, no timestamps |

`text` is accepted as an alias for `plain`; the canonical value is `plain`. A project without
lyrics returns `E_NOT_FOUND`.

## 2. `lyrics_search` — online lookup (read-only, network)

| Arg | Meaning |
| --- | --- |
| `project?` | Only supplies the default query (project name) and the track duration. An ambiguous project reference does **not** fail the search |
| `query?` | Free-text query. Defaults to the project name when no other query field is given |
| `track?` / `artist?` / `album?` | Exact-match fields |
| `source?` | `all` (default) / `karalyr` / `lrclib` / `lyricsOvh` |
| `limit?` | 1…50, default 10 |
| `index?` | Also fetch that 0-based result's full lyrics text |

Requires at least one query field (or a resolvable `project` name). `lyricsOvh` has no search
API: it needs **both** `track` and `artist`, and returns one result.

Result: `{ query, source, count, totalCount, statuses, results[] }`; each result has `index`,
`track`, `artist`, `album`, `duration`, `source`. With `index` it also returns
`selectedIndex`, `lyricsText` and `detectedFormat` — pass `lyricsText` straight to
`lyrics_import` and skip the round trip of copying the whole text back through the model.

If every upstream fails → `E_LYRICS_SOURCE` (network or source problem, **not** a paywall and
not a bad argument). Say so plainly, try another `source`, or import text directly.

## 3. `lyrics_import` — parse and save (writes)

| Arg | Meaning |
| --- | --- |
| `project?` | Target project; omit when only one exists |
| `text` | **Required.** Standard LRC, word-by-word LRC, enhanced word-level LRC (`[mm:ss.xx]<mm:ss.xx>字…`) or plain lyrics |
| `title?` / `artist?` / `album?` | Override/add metadata tags |
| `offset?` | Initial global offset in seconds, -60…60 |
| `keepOffset?` | Keep the previous offset when replacing. Default `false` (offset resets to 0). Mutually exclusive with `offset` |

Parsing uses the same `LyricsParserFactory` as the in-app import sheet, so word-level
timestamps and metadata survive exactly as they would from a manual paste. It **replaces**
any existing lyrics. Result carries `format`, `lineCount`, `wordCount`, `timedLineCount`,
`offset`, `title`, `artist`, `replaced`, plus the new `revision` and `snapshotId`.

Unparseable text → `E_INVALID_ARG` with the offending reason (empty / bad timestamp /
unrecognized format / no content). Both writing tools honour `dryRun` and `expectRevision`;
use them when overwriting lyrics someone may have edited in the app. A successful import also
refreshes the player's in-memory lyrics when that project is open.

## 4. `lyrics_offset` — global shift (writes)

Exactly one of `offset` (absolute, -60…60), `delta` (relative, -60…60, result must stay in
range) or `reset: true`. No lyrics imported yet → `E_NOT_FOUND`.

The model has two offsets: `metadata.offset` comes from the source file's `[offset:]` tag and
is **never** modified by this tool; `userOffset` is what the in-app offset panel changes. The
result reports `previousOffset`, `offset` (the new `userOffset`), `effectiveOffset`
(`metadata.offset + userOffset`, the value rendering actually uses) and `format`.

## Playbook

```
project_list    {}                                        # find the project id
lyrics_search   { project: "<id>", index: 0 }             # name as query, get text in one call
lyrics_import   { project: "<id>", text: "<lyricsText>",
                  dryRun: true }                          # validate the parse
lyrics_import   { project: "<id>", text: "<lyricsText>" } # write, note the new revision
lyrics_get      { project: "<id>", format: "json" }       # read back lines / word timestamps
lyrics_offset   { project: "<id>", delta: -0.3,
                  expectRevision: "<rev>" }               # fine-tune against the recording
```

If the user already has LRC text (a file, a paste, or hand-written word timing), skip the
search and go straight to `lyrics_import`. Search results can differ from the recording in the
project (live version, remaster, different take) — when timings look globally wrong, use
`lyrics_offset` with `delta`, or re-import a correctly timed LRC rather than editing individual
lines.
