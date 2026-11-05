#!/usr/bin/env bash
#
# snapshot.sh — save every readable surface of a project before changing it.
#
# Not a backup and not a restore path: the app writes its own snapshot before every
# mutation. This gives a human or an agent a comparable baseline of "what it looked
# like before", as plain JSON files plus the revision to pass as expectRevision.
#
# Usage
#   ./scripts/snapshot.sh [project] [--out DIR]
#   SPLITJAM_TOKEN=<token> ./scripts/snapshot.sh <id> --out /tmp/before
#
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$HERE/mcp.py" snapshot "$@"
