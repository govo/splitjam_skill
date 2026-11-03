#!/usr/bin/env bash
#
# snapshot.sh — save every readable surface of a project as JSON before changing it.
#
# Not a backup and not a restore path: the app keeps its own snapshots (it writes one before
# every mutation). This just gives a human or an agent a comparable baseline of "what it
# looked like before".
#
# Usage
#   ./snapshot.sh [project] [outdir] [extra global flags...]
#   ./snapshot.sh "" /tmp/snap --bridge-dir /tmp/splitjam-bridge-test
#
# Deliberately avoids `arr=()` + `"${arr[@]}"`: bash 3.2 expands an empty array into one
# empty argument, which turns into `splitjam --json "" ...` and fails with "Missing command".
# Every array expansion below is length-guarded for that reason.
set -uo pipefail

BIN="${SPLITJAM_BIN:-splitjam}"
PROJECT="${1:-}"
OUTDIR="${2:-./splitjam-snapshots/$(date +%Y%m%d-%H%M%S)}"
shift $(( $# > 2 ? 2 : $# ))

EXTRA=()
for arg in "$@"; do
  EXTRA[${#EXTRA[@]}]="$arg"
done

mkdir -p "$OUTDIR"

snap() {
  local name="$1"; shift
  local tmp="$OUTDIR/$name.json"
  local args=(--json)
  local arg
  for arg in "$@"; do
    args[${#args[@]}]="$arg"
  done
  if [ -n "$PROJECT" ]; then
    args[${#args[@]}]="--project"
    args[${#args[@]}]="$PROJECT"
  fi
  if [ "${#EXTRA[@]}" -gt 0 ]; then
    for arg in "${EXTRA[@]}"; do
      args[${#args[@]}]="$arg"
    done
  fi
  if "$BIN" "${args[@]}" >"$tmp" 2>"$OUTDIR/$name.err"; then
    rm -f "$OUTDIR/$name.err"
    echo "  ok   ${name}"
  else
    echo "  fail ${name} (see ${name}.err)"
  fi
}

echo "snapshot -> $OUTDIR"
snap project     project get
snap tracks      track list
snap beat        beat get
snap sections    section list
snap chords      chord get
snap lyrics      lyrics get --format json
snap entitlement entitlement get

REV="$(python3 - "$OUTDIR/project.json" <<'PY'
import json, sys
try:
    print(json.load(open(sys.argv[1])).get("revision") or "")
except Exception:
    print("")
PY
)"
if [ -n "$REV" ]; then
  echo "$REV" >"$OUTDIR/revision.txt"
  echo "revision: $REV"
  echo "pass it to later writes: --expect-revision $REV"
fi
