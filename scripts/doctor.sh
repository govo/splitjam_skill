#!/usr/bin/env bash
#
# doctor.sh — one health check, in plain language.
#
# An MCP client that will not connect has four different causes and they need four
# different fixes: nothing is listening, the token is wrong, no token was supplied,
# or the app is running with a permission tier that refuses every write. This prints
# which one it is, plus the fix, without asking the user to read JSON.
#
# Usage
#   ./scripts/doctor.sh
#   SPLITJAM_TOKEN=<token> ./scripts/doctor.sh
#
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$HERE/mcp.py" doctor "$@"
