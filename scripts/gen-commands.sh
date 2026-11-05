#!/usr/bin/env bash
#
# gen-commands.sh — regenerate references/commands.md from the CLI's own command table.
#
# The source of truth is `splitjam docs --json`, which prints the table the parser actually
# uses. Rendering the reference from it means the docs can never describe a command that does
# not exist, or miss one that does.
#
# Usage
#   ./scripts/gen-commands.sh
#   SPLITJAM_BIN=/path/to/splitjam ./scripts/gen-commands.sh
#
set -euo pipefail

HERE="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$HERE/references/commands.md"

find_bin() {
  if [ -n "${SPLITJAM_BIN:-}" ]; then printf '%s' "$SPLITJAM_BIN"; return; fi
  if command -v splitjam >/dev/null 2>&1; then command -v splitjam; return; fi
  for candidate in \
    "$HERE/../../demucs/cli/.build/release/splitjam" \
    "$HERE/../../demucs/cli/.build/debug/splitjam"; do
    if [ -x "$candidate" ]; then printf '%s' "$candidate"; return; fi
  done
}

BIN="$(find_bin)"
if [ -z "$BIN" ]; then
  echo "gen-commands.sh: splitjam not found." >&2
  echo "                 install it (brew install govo/tap/splitjam) or set SPLITJAM_BIN." >&2
  exit 2
fi

mkdir -p "$(dirname "$OUT")"

# The JSON goes to a file rather than a pipe: `python3 - <<'PY'` reads its program from stdin,
# so a pipe would be swallowed and the parser would see an empty document.
JSON_TMP="$(mktemp "${TMPDIR:-/tmp}/splitjam-docs.XXXXXX")"
SCRIPT_TMP="$(mktemp "${TMPDIR:-/tmp}/splitjam-render.XXXXXX").py"
trap 'rm -f "$JSON_TMP" "$SCRIPT_TMP"' EXIT

"$BIN" docs --json > "$JSON_TMP"

cat > "$SCRIPT_TMP" <<'PY'
import json
import sys

json_path, out_path = sys.argv[1], sys.argv[2]
doc = json.load(open(json_path))
commands = doc["commands"]
version = doc.get("version", "?")

GROUPS = {
    "ping": "Diagnostics", "version": "Diagnostics", "capabilities": "Diagnostics",
    "schema": "Diagnostics",
    "entitlement": "Entitlement",
    "project": "Projects",
    "track": "Tracks",
    "mixer": "Mixer",
    "beat": "Beat grid",
    "metronome": "Metronome",
    "section": "Sections",
    "chord": "Chords",
    "lyrics": "Lyrics",
}


def group_of(path):
    head = path.split(" ")[0]
    return GROUPS.get(head, head.capitalize())


ordered = []
for command in commands:
    name = group_of(command["path"])
    if name not in ordered:
        ordered.append(name)

lines = [
    "# Command reference",
    "",
    "Generated from `splitjam docs --json` (CLI %s). **Do not edit by hand** —" % version,
    "run `scripts/gen-commands.sh` after changing the CLI command table.",
    "",
    "Every command also accepts the global flags: `--json`, `--project`, `--expect-revision`,",
    "`--dry-run`, `--yes`, `--strict`, `--no-app-prompt`, `--timeout`, `--port`, `--token`.",
    "Flags may appear before or after the command.",
    "",
]

for name in ordered:
    members = [c for c in commands if group_of(c["path"]) == name]
    lines.append("## %s" % name)
    lines.append("")
    lines.append("| Command | Description | Parameters |")
    lines.append("| --- | --- | --- |")
    for command in members:
        usage = command["usage"].replace("|", "\\|")
        summary = command["summary"].replace("|", "\\|")
        params = []
        for positional in command.get("positionals", []):
            params.append("`%s` (%s)" % (positional["name"], positional["type"]))
        for flag, kind in sorted((command.get("flags") or {}).items()):
            params.append("`--%s` (%s)" % (flag, kind))
        cell = "<br>".join(params) if params else "—"
        lines.append("| `%s` | %s | %s |" % (usage, summary, cell))
    lines.append("")

lines.extend([
    "## Local commands (never talk to the app)",
    "",
    "| Command | Description |",
    "| --- | --- |",
    "| `splitjam doctor` | Presence, endpoint, every SplitJam instance on 48321–48330, token state and entitlement. Exits 3 when the app is closed but still prints everything. |",
    "| `splitjam docs [--json]` | This table, as text or JSON. |",
    "| `splitjam --version` | CLI version only. |",
    "",
])

with open(out_path, "w") as handle:
    handle.write("\n".join(lines))

print("wrote %s (%d commands)" % (out_path, len(commands)))
PY

python3 "$SCRIPT_TMP" "$JSON_TMP" "$OUT"
