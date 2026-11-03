# Playbooks

Each playbook is a complete chain you can type as-is, including the failure branches. When you
forget a flag, come back and copy.

## A. Build a practice version from scratch

Goal: 92 BPM, downbeat at 0.35s, keep drums and bass, cut one chorus section.

```bash
splitjam --json doctor                       # 1 precondition: must be running
splitjam --json project list                 # 2 find the project id
splitjam --json project get <id>             # 3 inspect tracks and whether a grid exists

splitjam --json beat get --project <id>      # 4 check mode
splitjam --json beat mode --mode tap --project <id>
splitjam --json beat bpm 92 --project <id>
splitjam --json beat anchor set --at 0.35 --project <id>
splitjam --json beat get --project <id>      # 5 verify applied.bpm

splitjam --json track mute stem:guitar --project <id>
splitjam --json track mute stem:vocals --project <id>
# mute the rest the same way; do not fake multi-solo

splitjam --json section create --start 72 --end 96 --title Chorus --project <id>
splitjam --json project get <id>             # 6 final revision for the report
```

Failure branches:
- step 4 shows `mode` already `tap` → skip the mode line;
- `beat bpm` returns `E_MODE` → still in automatic mode, go back one step;
- `beat anchor` returns `E_ANCHOR_FAR` → the time is too far from a beat; pick a closer one or
  stay in tap mode;
- `section create` returns `E_PRO_REQUIRED` → **stop**, report per §5 of SKILL.md, never delete
  existing sections to make room.

## B. Cut several sections

```bash
splitjam --json beat get --project <id>                 # bar length = 60/bpm*beatsPerBar
splitjam --json section list --project <id>              # how many are used (free tier: 3)
splitjam --json section create --start 72 --end 84 --title "Chorus 1" --project <id> --dry-run
splitjam --json section create --start 72 --end 84 --title "Chorus 1" --project <id> --yes
```

Always `--dry-run` first. Overlapping sections are neither merged nor rejected — compute the
ranges yourself and mention any overlap in the report so the user is not surprised later.

## C. Mixer-only changes

```bash
splitjam --json track list --project <id>
splitjam --json track pan "Lead Guitar" --value -0.3 --project <id>
splitjam --json track gain stem:drums --value 1.4 --project <id>
splitjam --json track get "Lead Guitar" --project <id>
```

When `track gain` returns `W_CLAMPED`, the report must carry both numbers: "you asked for 1.4,
the free tier caps at 1.0, 1.0 was written". Never say "set to 1.4".

## D. Export a slice for an external tool

```bash
splitjam --json track audio file stem:drums --project <id>          # does the asset exist
splitjam --json track audio peaks stem:drums --buckets 800 --project <id>
splitjam --json track audio slice stem:drums --range 12-24 --out ~/Desktop/drums-12-24.wav --project <id>
```

At most 300 seconds per call. For a whole song, state the plan first ("N slices, each X long"),
then do it.

## E. Handling a free-tier wall

```bash
splitjam --json entitlement get
# look at weekly_separation_limit / stem_split_pro / multi_stem_export / multiple_sections
splitjam --json section create --start 0 --end 10 --title A --project <id>
# if it returns E_PRO_REQUIRED
splitjam --json entitlement get            # confirm reason: entitlement or quota
```

Then do exactly one thing: state the conclusion and stop.

- `entitlement` → "this is a Pro feature, the app already showed its prompt, retry after
  upgrading"
- `quota` → "the free quota is used up, next available at X"

No retrying with different parameters, no splitting one operation into several to dodge a
limit, no pushing the upgrade.

## F. Revision conflict

```bash
splitjam --json track pan stem:bass --value 0.2 --project <id> --expect-revision 7f3a91c2
# E_CONFLICT_REVISION; error.hint carries the current revision
splitjam --json project get <id>            # re-read and see what changed
# write again with the new revision
```

A conflict means someone changed the project after your read — usually the user, in the UI.
Do **not** drop `--expect-revision` and write anyway; that overwrites their edit.
