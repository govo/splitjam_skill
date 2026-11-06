#!/usr/bin/env python3
"""
mcp.py — talk to SplitJam's local MCP server without any CLI.

The app hosts an MCP server (Streamable HTTP, JSON-RPC 2.0) at
http://127.0.0.1:48321/mcp. An agent that has it registered in its MCP config
calls the tools directly and never needs this file. This script exists for the
cases where a client cannot be configured, or where something is wrong and
"which part is broken" has to be answered from a shell:

    ./mcp.py doctor                 # endpoint, token, permission, tool count
    ./mcp.py health                 # raw GET /health (no token needed)
    ./mcp.py tools                  # tools/list as JSON
    ./mcp.py tools --markdown       # same, rendered as references/tools.md
    ./mcp.py call project_list
    ./mcp.py call track_gain '{"track":"stem:bass","value":0.8}'
    ./mcp.py call track_gain track=stem:bass value=0.8
    ./mcp.py call track_audio_slice '{"track":"stem:vocals","range":"0-60","mono":true}' --audio-dir /tmp/splitjam
    ./mcp.py snapshot [project] [--out DIR]

`track_audio_slice` returns the WAV as a second MCP content block. A shell client
cannot hand that block to a model, so `call` writes it to disk and prints the path
(`~/.cache/splitjam/audio` by default, override with `--audio-dir DIR` or
`$SPLITJAM_AUDIO_DIR`, disable with `--no-audio`). That file is what a transcription
step — or the user's own player — picks up.

Token lookup, first hit wins: --token, $SPLITJAM_TOKEN, ~/.config/splitjam/token.
The app keeps the real token inside its own sandbox; copy it once from
SplitJam → Settings → MCP Server. Nothing here tries to read the app's container.

Exit codes are for humans and shells only — the app no longer reports any:
0 ok · 1 the tool returned an error envelope · 2 usage · 3 app not reachable
· 11 token rejected · 12 handshake failed.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.request

DEFAULT_URL = "http://127.0.0.1:48321/mcp"
DEFAULT_HEALTH = "http://127.0.0.1:48321/health"
DEFAULT_AUDIO_DIR = "~/.cache/splitjam/audio"
TOKEN_FILE = pathlib.Path.home() / ".config" / "splitjam" / "token"
PROTOCOL_VERSION = "2025-06-18"
CLIENT_INFO = {"name": "splitjam-skill", "version": "1.0.0"}


# ---------------------------------------------------------------- transport


class Failure(Exception):
    def __init__(self, message: str, code: int = 1, hint: str | None = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.hint = hint


def find_token(explicit: str | None) -> str | None:
    if explicit:
        return explicit.strip()
    env = os.environ.get("SPLITJAM_TOKEN")
    if env and env.strip():
        return env.strip()
    try:
        text = TOKEN_FILE.read_text().strip()
    except OSError:
        return None
    return text or None


# A loopback request must never go through an HTTP proxy. Shells with Clash / corporate
# proxies export HTTP_PROXY globally, and urllib honours it even for 127.0.0.1 — the
# symptom is a confusing "502" from the proxy instead of "app not running".
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def http(url: str, body: dict | None, token: str | None, session: str | None = None):
    """One request. Returns (status, headers, raw body). Raises Failure when unreachable."""
    data = None
    headers = {"Accept": "application/json, text/event-stream"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if session:
        headers["Mcp-Session-Id"] = session

    request = urllib.request.Request(url, data=data, headers=headers,
                                     method="POST" if body is not None else "GET")
    try:
        with OPENER.open(request, timeout=20) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as error:
        return error.code, dict(error.headers or {}), error.read()
    except urllib.error.URLError as error:
        reason = getattr(error, "reason", error)
        raise Failure(
            f"Nothing answered at {url} ({reason}).",
            3,
            "SplitJam is not running, or the MCP server is off. Open the app, keep it "
            "running, and turn on Settings → MCP Server. Retrying will not help.",
        )
    except TimeoutError:
        raise Failure(
            f"{url} accepted the connection but did not answer in 20 s.",
            3,
            "The app's main thread is busy (separation, export). Retry once it is idle.",
        )


def parse_rpc(status: int, headers: dict, payload: bytes) -> dict:
    """Decode a JSON-RPC reply, tolerating an SSE-framed body."""
    text = payload.decode("utf-8", "replace").strip()
    if not text:
        raise Failure(f"Empty response body (HTTP {status}).", 12)
    content_type = headers.get("Content-Type") or headers.get("content-type") or ""
    if "text/event-stream" in content_type:
        chunks = [line[5:].strip() for line in text.splitlines() if line.startswith("data:")]
        text = chunks[-1] if chunks else text
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        raise Failure(f"Response is not JSON (HTTP {status}): {text[:300]}", 12)


class Client:
    def __init__(self, url: str, token: str | None):
        self.url = url
        self.token = token
        self.session: str | None = None

    def initialize(self) -> dict:
        status, headers, payload = http(self.url, {
            "jsonrpc": "2.0",
            "id": "initialize",
            "method": "initialize",
            "params": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": CLIENT_INFO,
            },
        }, self.token)

        if status == 401:
            raise Failure(
                "The MCP server rejected this token.",
                11,
                "Copy the token from SplitJam → Settings → MCP Server (regenerating it "
                "invalidates the old one), then set $SPLITJAM_TOKEN or write it to "
                f"{TOKEN_FILE} with 0600.",
            )
        if status != 200:
            raise Failure(f"initialize failed: HTTP {status} {payload[:200]!r}", 12)

        session = headers.get("Mcp-Session-Id") or headers.get("mcp-session-id")
        if not session:
            raise Failure("initialize returned no Mcp-Session-Id header.", 12)
        self.session = session

        # notifications/initialized is a notification: no id, no reply body.
        http(self.url, {"jsonrpc": "2.0", "method": "notifications/initialized"}, self.token, self.session)
        return parse_rpc(status, headers, payload).get("result") or {}

    def rpc(self, method: str, params: dict | None = None) -> dict:
        if not self.session:
            self.initialize()
        status, headers, payload = http(self.url, {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params or {},
        }, self.token, self.session)

        if status == 400:
            message = parse_rpc(status, headers, payload)
            # A stale session after an app restart: handshake again, once.
            if "session" in json.dumps(message).lower():
                self.session = None
                self.initialize()
                return self.rpc(method, params)
        if status != 200:
            raise Failure(f"{method} failed: HTTP {status} {payload[:300]!r}", 12)

        message = parse_rpc(status, headers, payload)
        if "error" in message:
            error = message["error"]
            hint = ((error.get("data") or {}).get("hint")) if isinstance(error.get("data"), dict) else None
            raise Failure(f"{method}: {error.get('message')} ({error.get('code')})", 12, hint)
        return message.get("result") or {}

    def call(self, tool: str, arguments: dict) -> dict:
        return self.rpc("tools/call", {"name": tool, "arguments": arguments})


def tool_envelope(result: dict) -> tuple[dict | None, list[str], list[dict]]:
    """Split a tools/call result into (envelope, text parts, non-text parts)."""
    texts: list[str] = []
    others: list[dict] = []
    envelope = None
    for part in result.get("content") or []:
        if part.get("type") == "text":
            texts.append(part.get("text") or "")
        else:
            others.append(part)
    if texts:
        try:
            envelope = json.loads(texts[0])
        except json.JSONDecodeError:
            envelope = None
    return envelope, texts, others


# ---------------------------------------------------------------- commands


def cmd_health(args) -> int:
    status, _, payload = http(args.health, None, None)
    if status != 200:
        raise Failure(f"/health answered HTTP {status}", 3)
    print(json.dumps(json.loads(payload), indent=2, ensure_ascii=False))
    return 0


def cmd_tools(args) -> int:
    client = Client(args.url, find_token(args.token))
    result = client.rpc("tools/list")
    tools = result.get("tools") or []
    if args.markdown:
        print(render_tools_markdown(tools))
    else:
        print(json.dumps(tools, indent=2, ensure_ascii=False))
    return 0


def audio_dir_for(args) -> pathlib.Path:
    return pathlib.Path(
        args.audio_dir or os.environ.get("SPLITJAM_AUDIO_DIR") or DEFAULT_AUDIO_DIR
    ).expanduser()


def save_audio_parts(parts: list[dict], envelope: dict | None, tool: str, directory: pathlib.Path) -> None:
    """Write every audio content block to disk and print where it landed.

    The app already wrote the WAV into its own container, but that path is outside the
    sandbox and unreadable here. This is the only copy a transcription step can use.
    """
    for part in parts:
        if part.get("type") != "audio":
            continue
        data = part.get("data") or ""
        mime = part.get("mimeType") or "audio/wav"
        if not data:
            print(f"[audio {mime}: empty payload]", file=sys.stderr)
            continue
        try:
            raw = base64.b64decode("".join(data.split()), validate=True)
        except (binascii.Error, ValueError):
            # A truncated base64 body is a transport problem, not a tool error: say so
            # instead of writing a half WAV that later decodes to silence.
            print(f"[audio {mime}: base64 payload did not decode — not saved]", file=sys.stderr)
            continue
        suffix = ".wav" if "wav" in mime else ".bin"
        # The envelope nests tool output under `result`, so the slice's own file name —
        # which carries track and range — lives one level down.
        bodies = (envelope or {}).get("result") or {}
        name = bodies.get("file") or f"{tool}-{int(time.time())}{suffix}"
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / pathlib.Path(name).name
        path.write_bytes(raw)
        duration = bodies.get("duration")
        span = f"{duration:.1f}s, " if isinstance(duration, (int, float)) else ""
        print(f"audio    {path} ({span}{len(raw) / 1_000_000:.2f} MB)")


def cmd_call(args) -> int:
    arguments = parse_arguments(args.arguments)
    client = Client(args.url, find_token(args.token))
    result = client.call(args.tool, arguments)
    envelope, texts, others = tool_envelope(result)

    if envelope is not None:
        print(json.dumps(envelope, indent=2, ensure_ascii=False))
    else:
        for text in texts:
            print(text)
    if args.no_audio:
        for part in others:
            if part.get("type") == "audio":
                data = part.get("data") or ""
                print(f"[audio {part.get('mimeType', 'audio/wav')}, {len(data) * 3 // 4} bytes as base64, not saved]", file=sys.stderr)
    else:
        save_audio_parts(others, envelope, args.tool, audio_dir_for(args))
    return 1 if result.get("isError") else 0


def cmd_doctor(args) -> int:
    token = find_token(args.token)
    print(f"endpoint : {args.url}")

    try:
        health = json.loads(http(args.health, None, None)[2])
    except Failure as failure:
        print("presence : not running")
        print(f"x {failure.message}")
        print(f"  fix    : {failure.hint}")
        print("  nothing was modified.")
        return 3
    except json.JSONDecodeError:
        print("presence : not SplitJam")
        print("x something answers /health with a non-JSON body.")
        print("  fix    : quit whatever holds 48321, or change the port in the app.")
        return 3

    print("presence : running")
    print(f"app      : {health.get('appVersion')} ({health.get('buildVersion')}) · pid {health.get('pid')}")
    print(f"protocol : MCP {health.get('protocolVersion')} · schema {health.get('schemaVersion')} · {health.get('toolCount')} tools")
    print(f"token    : {'present' if token else 'missing'}")
    permission = health.get("permission", "unknown")
    suffix = " (every write returns E_FORBIDDEN)" if permission == "read" else ""
    print(f"permit   : {permission}{suffix}")
    print()

    if not token:
        print("x no token: set $SPLITJAM_TOKEN or write it to", TOKEN_FILE)
        print("  fix    : SplitJam → Settings → MCP Server → Copy token, then")
        print(f"           mkdir -p {TOKEN_FILE.parent} && printf %s '<token>' > {TOKEN_FILE} && chmod 600 {TOKEN_FILE}")
        print("  nothing was modified.")
        return 11

    client = Client(args.url, token)
    try:
        info = client.initialize()
    except Failure as failure:
        print(f"x {failure.message}")
        if failure.hint:
            print(f"  fix    : {failure.hint}")
        print("  nothing was modified.")
        return failure.code

    print(f"server   : {info.get('serverInfo', {}).get('name')} {info.get('serverInfo', {}).get('version')}")
    tools = (client.rpc("tools/list").get("tools") or [])
    print(f"tools    : {len(tools)} visible")
    print()
    print("ok ready to work.")
    if permission == "read":
        print("  note   : permission is read-only — raise it in Settings → MCP Server.")
    return 0


def cmd_snapshot(args) -> int:
    project = args.project or ""
    outdir = pathlib.Path(args.out or f"./splitjam-snapshots/{time_stamp()}")
    outdir.mkdir(parents=True, exist_ok=True)
    client = Client(args.url, find_token(args.token))

    def base() -> dict:
        return {"project": project} if project else {}

    plan = [
        ("project", "project_get", {}),
        ("tracks", "track_list", {}),
        ("beat", "beat_get", {}),
        ("sections", "section_list", {}),
        ("chords", "chord_get", {}),
        ("lyrics", "lyrics_get", {"format": "json"}),
        ("entitlement", "entitlement_get", {}),
    ]

    print(f"snapshot -> {outdir}")
    revision = None
    for name, tool, extra in plan:
        arguments = dict(base())
        arguments.update(extra)
        try:
            result = client.call(tool, arguments)
        except Failure as failure:
            (outdir / f"{name}.err").write_text(f"{failure.message}\n{failure.hint or ''}\n")
            print(f"  fail {name} (see {name}.err)")
            continue
        envelope, texts, _ = tool_envelope(result)
        body = envelope if envelope is not None else {"text": "\n".join(texts)}
        (outdir / f"{name}.json").write_text(json.dumps(body, indent=2, ensure_ascii=False) + "\n")
        if result.get("isError"):
            print(f"  fail {name} (tool error, see {name}.json)")
            continue
        print(f"  ok   {name}")
        if name == "project" and body.get("revision"):
            revision = body["revision"]

    if revision:
        (outdir / "revision.txt").write_text(revision + "\n")
        print(f"revision: {revision}")
        print(f"pass it to later writes as expectRevision: {revision}")
    return 0


def time_stamp() -> str:
    import datetime
    return datetime.datetime.now().strftime("%Y%m%d-%H%M%S")


# ---------------------------------------------------------------- helpers


def parse_arguments(raw: list[str]) -> dict:
    """Accept one JSON object, `-` for stdin, or bare key=value / key:=json pairs."""
    if not raw:
        return {}
    if raw == ["-"]:
        text = sys.stdin.read().strip()
        return json.loads(text) if text else {}
    if len(raw) == 1 and raw[0].lstrip().startswith("{"):
        return json.loads(raw[0])
    arguments: dict = {}
    for item in raw:
        if ":=" in item:
            key, value = item.split(":=", 1)
            arguments[key] = json.loads(value)
        elif "=" in item:
            key, value = item.split("=", 1)
            arguments[key] = coerce(value)
        else:
            raise Failure(f"Not an argument: {item!r}", 2, "Use key=value, key:=<json>, or one JSON object.")
    return arguments


def coerce(value: str):
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered == "null":
        return None
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def render_tools_markdown(tools: list[dict]) -> str:
    order = ["project", "track", "audio", "mixer", "beat", "metronome", "section",
             "chord", "lyrics", "entitlement", "diagnostic", "misc"]
    titles = {
        "project": "Projects", "track": "Tracks", "audio": "Audio",
        "mixer": "Mixer", "beat": "Beat grid", "metronome": "Metronome",
        "section": "Sections", "chord": "Chords", "lyrics": "Lyrics",
        "entitlement": "Entitlement", "diagnostic": "Diagnostics", "misc": "Other",
    }

    grouped: dict[str, list[dict]] = {}
    for tool in tools:
        category = (tool.get("title") or "").split(".")[0] or "misc"
        grouped.setdefault(category, []).append(tool)

    def sort_key(category: str) -> tuple[int, str]:
        return (order.index(category) if category in order else len(order), category)

    lines = [
        "# Tool reference",
        "",
        f"Generated from `tools/list` ({len(tools)} tools, schema negotiated at handshake).",
        "**Do not edit by hand** — run `scripts/gen-tools.sh` against a running app.",
        "",
        "Tool names are the operation ids with `.` replaced by `_` (`track.audio.slice` →",
        "`track_audio_slice`). Some MCP clients prefix them with the server name, e.g.",
        "`mcp__splitjam__track_gain`.",
        "",
        "Every tool also accepts `project` (omit when the app has exactly one project).",
        "Writing tools accept `dryRun` and `expectRevision`.",
        "",
    ]

    for category in sorted(grouped, key=sort_key):
        lines.append(f"## {titles.get(category, category.capitalize())}")
        lines.append("")
        lines.append("| Tool | Description | Parameters |")
        lines.append("| --- | --- | --- |")
        for tool in sorted(grouped[category], key=lambda t: t.get("name", "")):
            schema = tool.get("inputSchema") or {}
            properties = schema.get("properties") or {}
            required = set(schema.get("required") or [])
            params = []
            for name, spec in properties.items():
                kind = spec.get("type", "any")
                if spec.get("enum"):
                    kind = " \\| ".join(str(value) for value in spec["enum"])
                if "minimum" in spec and "maximum" in spec:
                    kind += f" {spec['minimum']}...{spec['maximum']}"
                marker = "" if name in required else "?"
                params.append(f"`{name}{marker}` ({kind})")
            description = (tool.get("description") or "").replace("|", "\\|")
            cell = "<br>".join(params) if params else "—"
            lines.append(f"| `{tool.get('name')}` | {description} | {cell} |")
        lines.append("")

    lines.append("`?` marks an optional parameter. Required ones have no marker.")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------- entry


def main() -> int:
    parser = argparse.ArgumentParser(description="Call SplitJam's local MCP server.")
    parser.add_argument("--url", default=os.environ.get("SPLITJAM_URL", DEFAULT_URL))
    parser.add_argument("--health", default=os.environ.get("SPLITJAM_HEALTH", DEFAULT_HEALTH))
    parser.add_argument("--token", default=None, help="bearer token; prefer $SPLITJAM_TOKEN")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("health", help="GET /health (no token needed)")
    tools_parser = sub.add_parser("tools", help="tools/list")
    tools_parser.add_argument("--markdown", action="store_true")

    call_parser = sub.add_parser("call", help="tools/call")
    call_parser.add_argument("tool")
    call_parser.add_argument("arguments", nargs="*")
    call_parser.add_argument("--audio-dir", default=None,
                             help="where returned audio content blocks are written "
                                  "(default ~/.cache/splitjam/audio, or $SPLITJAM_AUDIO_DIR)")
    call_parser.add_argument("--no-audio", action="store_true",
                             help="discard audio content blocks instead of saving them")

    sub.add_parser("doctor", help="presence, token, permission, tool count")

    snapshot_parser = sub.add_parser("snapshot", help="save every readable surface of a project")
    snapshot_parser.add_argument("project", nargs="?", default="")
    snapshot_parser.add_argument("--out", default=None)

    args = parser.parse_args()
    handler = {
        "health": cmd_health, "tools": cmd_tools, "call": cmd_call,
        "doctor": cmd_doctor, "snapshot": cmd_snapshot,
    }[args.command]
    try:
        return handler(args)
    except Failure as failure:
        print(f"x {failure.message}", file=sys.stderr)
        if failure.hint:
            print(f"  fix: {failure.hint}", file=sys.stderr)
        return failure.code
    except json.JSONDecodeError as error:
        print(f"x bad JSON: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
