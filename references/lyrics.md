# Lyrics

**One sentence from the user is enough.** "Find the lyrics for this song", "identify the
lyrics", "give me word-by-word so the highlight follows the voice", "the lyrics are 0.4s
late" — all of them resolve to the same chain in §2. The defaults are already decided there;
do not open with a questionnaire about which source, which result or which format.

A prompt copied from SplitJam's empty lyrics panel ("Use the `splitjam` skill …" plus a
`Project:` line) is this same job with the target already named — see `SKILL.md` §4.1,
"A prompt copied from the app's empty lyrics panel", for resolving the project. It is not a
new workflow: run the chain in §2 as written.

The house default is **word-level**. Line-level is a downgrade you have to justify.

## 0. Who listens, who writes

The app does **not** transcribe audio. That is the agent's job — and the app is built for it:
it hands out the separated vocal stem, and it takes back whatever lyrics text you write.

| The user imagines | What actually happens | Who does it |
| --- | --- | --- |
| "listen to the song and write the words down" | no ASR in the app; `track_audio_slice` returns the vocal stem as audio | **you** |
| "it must already have the lyrics somewhere" | three public catalogs | `lyrics_search` |
| "word-by-word / karaoke timing" | you write the word tags, or the catalog entry already has them | you / source |
| "the whole thing is 0.4s early" | one global shift | `lyrics_offset` |
| "this one line is wrong" | edit the LRC text in the app's import panel | user |

So "identify the lyrics" = **get the words from a catalog or from your own ears, then write
word-level timing**. The user does not need the division of labour explained, but the report
must say which of the three it was: `searched`, `transcribed`, `aligned`.

## 1. Word-level: the only two shapes the parser accepts

Both are real LRC, and both round-trip through the in-app import sheet. Anything else falls
back to line-level without an error.

**Enhanced (preferred — the line tag is optional, the `<…>` tags are not):**

```
[ti:羽毛鳞刺]
[ar:Dear Jane]
[00:12.34]<00:12.34>往<00:12.56>日<00:12.78>的<00:13.00>歌
```

**Word standard (several `[mm:ss.xx]` on one line, no line tag):**

```
[ti:羽毛鳞刺]
[ar:Dear Jane]
[00:12.34]往 [00:12.56]日 [00:12.78]的 [00:13.00]歌
```

Rules that decide whether the import stays word-level — get these wrong and it silently
degrades:

| Rule | Why it matters |
| --- | --- |
| Timestamp is `mm:ss.xx` or `mm:ss.xxx` — two-digit minutes, two-digit seconds, 2–3 decimals | any other shape is not a tag; the word is swallowed into the previous one |
| **Word standard needs ≥ 2 tags on a line** | a single tag is indistinguishable from a normal LRC line, so that line becomes line-level |
| Word text follows its tag directly — no leading space in enhanced | the space becomes part of the word and widens the highlight |
| Metadata rows (`[ti:]` `[ar:]` `[al:]` `[by:]` `[offset:]`) sit above the first lyric line | they are only read on lines that carry no word tags |
| Do not mix `[..]`-per-word and `<..>`-per-word in one file | one `<` anywhere selects the enhanced parser, which then drops the `[..]` word rows |
| The line tag is optional in enhanced; when present, keep it ≤ its first word tag | the line start is what the panel scrolls to and what `endTime` chains from |

The result's `format` tells you what landed: `wordEnhanced`, `wordStandard`, `lrc`,
`plainText`. `wordCount` is the number that matters — `wordCount == 0` means line-level.

## 2. The default chain

Four routes, tried in this order. Stop at the first one that yields word-level output.

| Route | When | Cost |
| --- | --- | --- |
| **L0 — it is already there** | `lyrics_get` → `wordCount > 0` | one call |
| **L1 — the catalog has word tags** | `lyrics_search` → `detectedFormat` is `wordEnhanced` / `wordStandard` | two calls |
| **L2 — catalog text, your timing** | catalog has the words at line level, the vocal stem exists | a few audio calls |
| **L3 — you transcribe it all** | nothing usable online, but the vocal stem exists | one audio call per minute |
| **L4 — no audio path** | the client cannot take audio and nothing online has timing | honest line-level |

```bash
./scripts/mcp.py call lyrics_get    '{ "format": "json" }'                       # L0
./scripts/mcp.py call lyrics_search '{ "project": "<id>", "limit": 10 }'         # L1 candidates
./scripts/mcp.py call lyrics_search '{ "project": "<id>", "index": 3 }'          # L1 text + detectedFormat
./scripts/mcp.py call track_audio_slice '{ "track": "stem:vocals", "range": "0-60", "mono": true }'   # L2 / L3
./scripts/mcp.py call lyrics_import '{ "project": "<id>", "text": "<lrc>", "dryRun": true }'
./scripts/mcp.py call lyrics_import '{ "project": "<id>", "text": "<lrc>" }'
./scripts/mcp.py call lyrics_get    '{ "project": "<id>", "format": "json" }'    # verify
```

| Step | Default decision, already made |
| --- | --- |
| 0 | `project` is omitted when the app holds exactly one project. With **no** project at all, search still works but nothing can be saved — report the sheet instead of importing. |
| 1 | Existing `wordCount > 0` and no "redo / replace / another version" in the request → **report and stop**. Replacing hand-timed lyrics is a regression. Existing line-level + user asked for word-level → replacing is the point, go ahead. |
| 2 | Search with `project` only: the project name is the default query, the project duration is the match anchor. Add `track` / `artist` when the name is a working title ("demo 3", "Untitled"). |
| 3 | Pick the result by §3, then re-search with `index` — one call returns `lyricsText` plus `detectedFormat`. |
| 4 | Word tags in the sheet → import and stop there. Line-level sheet → keep that text as the **transcript** and go to §4 for timing; do not re-transcribe what a catalog already spells correctly. |
| 5 | Nothing usable online → §4 with an empty transcript, i.e. transcribe the stem yourself. |
| 6 | `dryRun` first only when something is being replaced. On a clean project it is one wasted round trip. |
| 7 | Read back: `wordCount > 0`, `format` is the word form, `lineCount` matches the sheet. |
| 8 | Shift only if the user says so or line 1 is audibly off — once (§6). |

Carry the `revision` from the import into any `lyrics_offset` call via `expectRevision`.

## 3. Choosing a search result

`results[]` carries `track`, `artist`, `album`, `duration`, `source`. Rank by:

1. **Duration first.** `|result.duration − project.duration|` ≤ 5 s, smallest wins. A sheet
   for the 3:41 studio take is wrong for a 5:12 live recording even when the title matches.
2. **Exact title second.** Skip entries whose `track` carries `live`, `cover`, `remix`,
   `instrumental`, `karaoke version` or `remaster` when the project name does not.
3. **Source third.** `karalyr` most often ships word tags; `lrclib` sometimes; `lyricsOvh`
   **never** (it has no search endpoint and returns a plain block).
4. A `duration` of `null` is not a disqualifier — fall back to title + artist, and prefer a
   source that did return one.

If the top two are within half a second of each other and both titles match, take the one with
word tags and mention the other in the report; do not spend turns comparing them.

A catalog miss is not a dead end: you have the stem. Go to §4.

## 4. Listening to the vocal stem

This is the part people mean by "recognise the lyrics". The app gives you the isolated voice;
you supply the words and the timing.

**Preconditions.** `track_audio_file { track: "stem:vocals" }` must answer — a project that was
never separated has no stems and returns `E_NOT_FOUND`. Say the project needs separating in
the app; separation is not an MCP operation.

**Slice size.** `track_audio_slice` embeds the WAV in the same result, capped at **8 MiB of raw
bytes**. That is ~95 s of 44.1 kHz mono 16-bit (87 s at 48 kHz), half that in stereo. So:

| Setting | Value | Why |
| --- | --- | --- |
| `mono` | `true` | halves the payload, no loss for speech |
| slice length | **60 s** | comfortable margin under 8 MiB at any common sample rate |
| overlap | **2 s** with the next slice | a line cut in half at the seam is unrecoverable otherwise |
| `range` | `"0-60"`, `"58-118"`, … | the app clamps past the end and warns `W_RANGE_CLAMPED` |

Measured on a 44.1 kHz project: 10 s → 0.89 MB, 30 s → 2.65 MB, 60 s → 5.3 MB. The cap is on
raw bytes, before base64.

```bash
./scripts/mcp.py call track_audio_file  '{ "track": "stem:vocals" }'
./scripts/mcp.py call track_audio_slice '{ "track": "stem:vocals", "range": "0-60", "mono": true }'
# audio    ~/.cache/splitjam/audio/<id>_vocals_0-60_mono.wav (60.0s, 5.29 MB)
```

Two ways to actually hear it:

- **Native MCP client** (the app registered as a server): the `audio` content block lands in
  your context — listen to it directly.
- **This skill's CLI path**: `mcp.py call` writes the WAV to `~/.cache/splitjam/audio/` and
  prints the path. Hand that file to your client's audio-transcription step, or read it
  yourself if your model accepts audio files. If neither is available, you cannot transcribe —
  go to L4 and say so.

**Transcription discipline.**

- Write what is **sung**, in the original language. No translation, no romanisation, no
  paraphrase, no filling in lines you did not hear.
- One lyric line per sung phrase; do not merge two phrases to save a line.
- Background vocals and ad-libs go on their own line, prefixed `(`…`)`, and only when they are
  audible enough to matter. The lead line is the one the user is practising.
- Absolute time = slice start + local time. Overlap means a phrase can land in two slices:
  keep the fuller copy. The first line of a slice is often a fragment cut mid-word — drop it
  when the previous slice already covers that phrase.
- **Transcription comes back at phrase level** (`[mm:ss,mm:ss] text`), not per word. Those are
  your line times; word times still come from §5. "The transcriber gave no word timestamps" is
  not "line-level only" — it is exactly the L2/L3 case this whole section exists for.
- Announce the plan before a long song: "4 slices, ~60 s each" — not 12 silent calls.

The text is worth more than the timing. If the audio is too dense to place every syllable,
place the lines correctly and let §5 distribute the words inside them.

## 5. Putting timing on the words

Two inputs decide how much work this is: whether the line already has a start time, and how
much you trust your own ear. Either way the result is enhanced LRC.

**Pass 1 — inside a line, free.**

- Split the line into words at punctuation and whitespace; punctuation gets zero weight.
- Each word's share = its character count / the line's weighted character count.
- Walk from `line.startTime` to `line.endTime`, assigning in order; the last word ends at
  `line.endTime`. Never let a word cross a line boundary.

**Pass 2 — snap to the vocal envelope (one call, visibly better).**

```bash
./scripts/mcp.py call track_audio_peaks '{ "track": "stem:vocals",
                                           "buckets": 9600, "channel": "both" }'
```

- `peaks[]` holds `buckets` values over `duration` seconds: bucket `i` covers
  `[i·duration/N, (i+1)·duration/N]`, `N` = the returned `buckets`.
- Inside each line's window, mark an onset where the value rises by ≥ 0.05 and clears 0.15.
- More onsets than words → keep the loudest ones in order. Fewer onsets than words → merge the
  shortest gaps, or fall back to pass 1 for that line alone.
- Snap each word's start to its onset; the previous word ends there.

`buckets` above ~10 000 costs a lot of tokens for little gain — 40 buckets per second is
already finer than a sung syllable.

**Never present either pass as transcription.** The words are what you heard; the timestamps
are an estimate. The report says `aligned`, not `recognised word by word from the audio`.

## 6. Verifying, then correcting the offset

Read back with `lyrics_get { format: "json" }` and check three things: `format` is the word
format you intended, `wordCount` > 0, and each line's `words[].text` joined equals its `text`.

For timing the model has **two** offsets and only one of them is yours:

| Field | Comes from | Who changes it |
| --- | --- | --- |
| `metadata.offset` | the source file's `[offset:]` tag | nobody — `lyrics_offset` never touches it |
| `userOffset` | the in-app offset panel | `lyrics_offset` |
| `effectiveOffset` | `metadata.offset + userOffset` | this is what rendering uses — quote this one |

- "The lyrics are 0.4 s late" → the words must move **earlier** → `delta: -0.4`.
- One systematic shift per session. Two rounds means the sheet belongs to another recording:
  re-search by duration, or re-check the slice start you used as the time base.
- `reset: true` clears the user offset but leaves the file's own offset intact.

## 7. Failure branches

| Result | Meaning | Move |
| --- | --- | --- |
| `E_NOT_FOUND` "Track vocals has no audio file" | the project was never separated, or the stem was deleted | separate in the app; no MCP call can create it |
| `E_NOT_FOUND` on `lyrics_get` | no lyrics yet | search or transcribe — report the next step, not an error |
| text block "above the 8388608-byte inline limit" | the slice was too long for the inline block | halve the range (30 s) or set `mono: true` |
| `E_LYRICS_SOURCE` | every upstream failed, or the chosen one did | read `statuses` (`karalyr:3,lrclib:0(network)`) — network, not a paywall. Retry once, switch `source`, or go to §4 |
| `E_INVALID_ARG` on import | the text is not parseable (empty, bad timestamp, unrecognised format) | the hint names the reason; re-check the tag shape against §1 |
| `E_FORBIDDEN` | permission tier is **Read only** | the user raises it in Settings → MCP Server; not a paywall |
| `E_CONFLICT_REVISION` | someone edited the project after your read | re-read `project_get`, then write with the fresh revision |
| `W_RANGE_CLAMPED` | the range ran past the track end | the app used the clamped end; use `result.end` as the slice's real end |

## 8. What to report

Four lines, plus the numbers that prove it worked:

```
done       lyrics imported — 42 lines, 318 word timestamps (wordEnhanced)
project    Midnight Drive (a1b2c3d4)
source     transcribed from the vocal stem · timing aligned to the envelope
undo       lyrics_import with the previous sheet, or lyrics_offset { reset: true }
```

- Words from a catalog, timing from your ear → `source: catalog text, agent-timed`.
- Everything from the stem → `source: transcribed by the agent`.
- Line-level only → say `line-level, the highlight follows the line` instead of a word count,
  and say why (no audio path, or the user chose speed).
- Overwrote something → name what was replaced and its `wordCount`.
- Wanted a `.lrc` file → `lyrics_get { format: "lrc" }` returns the sheet in its **own**
  format, word tags included, ready to save. Do not rebuild the text by hand.
