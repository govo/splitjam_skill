#!/usr/bin/env bash
#
# gen-tools.sh — regenerate references/tools.md from a running app's `tools/list`.
#
# The app derives its tool table from one catalog (AutomationCatalog) and one parameter
# map. Reading the same table back over MCP means the reference cannot describe a tool
# that does not exist, or miss one that does.
#
# Usage
#   SPLITJAM_TOKEN=<token> ./scripts/gen-tools.sh
#
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HERE/../references/tools.md"

python3 "$HERE/mcp.py" tools --markdown > "$OUT.tmp"
mv "$OUT.tmp" "$OUT"
echo "wrote $OUT"
