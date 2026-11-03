#!/usr/bin/env bash
#
# doctor.sh — run `splitjam doctor --json` and turn it into one verdict plus a next step.
#
# Why the wrapper: doctor's JSON is for programs, but "why can't I use this" has to be said in
# plain language. When the app is closed doctor exits 3 yet still reports everything, so this
# script prints the full picture in both cases.
#
set -uo pipefail

BIN="${SPLITJAM_BIN:-splitjam}"

if ! command -v "$BIN" >/dev/null 2>&1; then
  echo "x splitjam not found. Run ./install.sh, or point SPLITJAM_BIN at the binary."
  exit 127
fi

OUT="$("$BIN" doctor --json "$@" 2>&1)"
CODE=$?

python3 - "$OUT" "$CODE" <<'PY'
import json, sys

raw, code = sys.argv[1], int(sys.argv[2])
try:
    payload = json.loads(raw)
except Exception:
    print("x doctor did not return parsable JSON:")
    print(raw.strip()[:800])
    sys.exit(code or 9)

res = payload.get("result") or {}
presence = res.get("presence", "unknown")
bridge = res.get("bridge") or {}
automation = res.get("automation") or {}
ent = res.get("entitlement") or {}
last = res.get("lastSeen") or {}

print(f"presence : {presence}")
print(f"bridge   : {bridge.get('path','?')}"
      f"{'' if bridge.get('writable') else '  (not writable)'}")
print(f"token    : {'present' if automation.get('tokenPresent') else 'missing'}"
      f" / valid={automation.get('tokenValid')}")
if ent:
    print(f"tier     : {ent.get('state','unknown')} (verified={ent.get('verification','unknown')})")
if last:
    print(f"lastSeen : app {last.get('appVersion','?')} · schema {last.get('schemaVersion','?')}")

print()

if presence == "running":
    print("ok ready to work.")
    sys.exit(0)

hints = {
    "starting": "The app is starting. Retry in a few seconds (or raise --wait-startup).",
    "stuck":    "The app is running but its heartbeat stopped. Bring SplitJam to the front, then retry.",
    "not-running": "Open SplitJam and retry; the window may be minimized, but the app must stay running.",
}
print("x " + hints.get(presence, "The app is unreachable."))
if not automation.get("tokenPresent"):
    print("  also: Settings → Command Line Access is off; turn it on and authorize.")
if last.get("stoppedAt"):
    print(f"  last seen: {last['stoppedAt']}")
print("  nothing was modified.")
sys.exit(code or 3)
PY
