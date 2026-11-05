#!/usr/bin/env bash
#
# doctor.sh — run `splitjam doctor --json` and turn it into one verdict plus a next step.
#
# Why the wrapper: doctor's JSON is for programs, but "why can't I use this" has to be said in
# plain language. When the app is closed doctor exits 3 yet still reports everything, so this
# script prints the full picture in both cases.
#
# The interesting case this exists for is port ambiguity: more than one SplitJam can be running
# (or something else can hold 48321). The JSON lists every candidate port, who answers on it and
# which one the CLI actually chose — this script makes that readable in three lines.
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
endpoint = res.get("endpoint") or {}
ports = res.get("ports") or {}
automation = res.get("automation") or {}
ent = res.get("entitlement") or {}
seen = res.get("lastSeen") or {}

instances = ports.get("splitjamInstances") or []
occupied = ports.get("occupiedByOtherApp") or []

pin = "pinned" if endpoint.get("pinned") else ("auto-discovered" if endpoint.get("discovered") else "preferred")
print(f"presence : {presence}")
if presence == "running":
    print(f"endpoint : {endpoint.get('url', '?')}  ({pin})")
if seen:
    print(f"app      : {seen.get('appVersion', '?')}"
          f" · schema {seen.get('schemaVersion', '?')} · pid {seen.get('pid', '?')}")
if len(instances) > 1 or occupied or (presence != "running" and instances):
    parts = []
    for instance in instances:
        label = f"{instance.get('port')}/pid {instance.get('pid')}"
        if not instance.get("compatible", True):
            label += f" (schema {instance.get('schemaVersion')}, skipped)"
        elif instance.get("tokenAccepted") is False:
            label += " (token rejected)"
        if instance.get("selected"):
            label += " <- selected"
        parts.append(label)
    if parts:
        print("instances: " + ", ".join(parts))
    if occupied:
        print("not SJ   : " + ", ".join(str(port) for port in occupied))

token_state = "present" if automation.get("tokenPresent") else "missing"
valid = automation.get("tokenValid")
if automation.get("tokenPresent"):
    token_state += f" · {automation.get('tokenSource') or 'unknown source'} · valid={valid}"
print(f"token    : {token_state}")
permission = automation.get("permission")
if permission:
    suffix = " (read-only: writes and deletes are refused)" if permission == "read" else ""
    print(f"permit   : {permission}{suffix}")
if ent:
    print(f"tier     : {ent.get('state', 'unknown')} (verified={ent.get('verification', 'unknown')})")

print()

if presence == "running" and valid is not False:
    print("ok ready to work.")
    if permission == "read":
        print("  note    : permission is read-only — any write returns E_FORBIDDEN (10).")
        print("            Raise it in Settings → Command Line Access → Permission.")
    sys.exit(0)
if presence == "running":
    print("x SplitJam is running, but it rejected this CLI's token.")
    print("  fix     : Settings → Command Line Access → copy the current token, then")
    print("            `splitjam auth --token <token>` (regenerating it invalidates the old one).")
    print("  nothing was modified.")
    sys.exit(9)

hints = {
    "not-ready": "Something that is not SplitJam holds the port. Quit it, or pin another one:"
                 " `splitjam auth --port <n>`.",
    "incompatible": "SplitJam is running, but not in a version this CLI understands.",
    "not-running": "Open SplitJam and retry; the window may be minimized, but the app must stay running.",
}
print("x " + hints.get(presence, "The app is unreachable."))
if presence == "not-ready" and occupied:
    print("  held by : " + ", ".join(str(port) for port in occupied))
incompatible = [i for i in instances if not i.get("compatible", True)]
if incompatible:
    versions = ", ".join(f"port {i.get('port')} speaks schema {i.get('schemaVersion')}" for i in incompatible)
    print(f"  version : {versions}; this CLI speaks schema {payload.get('schemaVersion', '?')}.")
    print("            update whichever is older — the app, or `./install.sh` for the CLI.")
if not automation.get("tokenPresent"):
    print("  also    : Settings → Command Line Access is off; turn it on, copy the token, then")
    print("            `splitjam auth --token <token>`.")
elif valid is False:
    print("  also    : the app rejected the stored token. Copy the current one from Settings →")
    print("            Command Line Access and run `splitjam auth --token <token>`.")
print("  nothing was modified.")
sys.exit(code or 3)
PY
