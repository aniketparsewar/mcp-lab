"""Day 1, Part A — the MCP protocol by hand (no SDK).

Before the framework, the wire. MCP over stdio is newline-delimited
JSON-RPC 2.0: one message per line. A REQUEST has an id and expects
exactly one response (a result OR an error). A NOTIFICATION has no
id and is NEVER answered. The session opens with a handshake:
initialize -> (response) -> notifications/initialized -> work.

Server policy for this lab (stated, so the checks are fair):
- Requests other than initialize, before initialize: error -32002.
- tools/list and tools/call before notifications/initialized: -32002.
- Unknown method: -32601. Bad tool name or bad arguments: -32602.
- Unparseable line: -32700 with id null (there is no id to echo).

Run from the mcp-lab root:  python exercises/day1.py
Done when every check prints PASS. Do not edit the checks.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "lab-server", "version": "0.1.0"}

TOOLS = [{
    "name": "chunk_text",
    "description": "Split a document into fixed-size character windows "
                   "with overlap (the W5 fixed chunker, as a tool).",
    "inputSchema": {
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "size": {"type": "integer", "default": 500},
            "overlap": {"type": "integer", "default": 50},
        },
        "required": ["text"],
    },
}]


def _result(rid, result) -> str:
    return json.dumps({"jsonrpc": "2.0", "id": rid, "result": result})


def _error(rid, code, message) -> str:
    return json.dumps({"jsonrpc": "2.0", "id": rid,
                       "error": {"code": code, "message": message}})


def chunk_text(text: str, size: int = 500, overlap: int = 50) -> list[str]:
    """TODO(you): W5's fixed windows, from the mechanism.

    Windows start at 0 and step (size - overlap); each window is
    text[start:start+size]; the last window may be short. Empty text
    -> []. Raise ValueError if size <= 0 or overlap is not in
    [0, size).
    """
    if size <= 0 or overlap >= size:
        raise ValueError("Invalid size or overlap")
    if overlap < 0:
        raise ValueError("Overlap must be non-negative")
    if text == "":
        return []
    chunks = []
    for i in range(0, len(text), size - overlap):
        chunks.append(text[i:i+size])
    return chunks


class McpServer:
    """One session's state + dispatch. Transport-free on purpose:
    lines in, lines (or None) out — stdio is just one way to feed it.
    """

    def __init__(self) -> None:
        self._handshake = False   # initialize received
        self._ready = False       # notifications/initialized received

    def handle_line(self, line: str) -> str | None:
        """TODO(you): parse, route, respond — per the policy above.

        Route sketch (yours to implement):
        - json.loads fails -> _error(None, -32700, ...)
        - no "id" key -> notification: notifications/initialized sets
          _ready (only meaningful after the handshake); return None.
        - method == "initialize" -> set _handshake; _result with
          protocolVersion, capabilities {"tools": {}}, serverInfo.
        - not _handshake -> _error(id, -32002, ...)
        - tools/list, tools/call when not _ready -> -32002.
        - tools/list -> _result(id, {"tools": TOOLS})
        - tools/call -> params {"name", "arguments"}: wrong name or
          missing/invalid arguments -> -32602; else run chunk_text
          and _result(id, {"content": [{"type": "text", "text":
          json.dumps(chunks)}], "isError": False}).
        - anything else -> _error(id, -32601, ...)
        The response id echoes the request id exactly.
        """
        try:
            data = json.loads(line)
            if "id" not in data:
                if data.get("method") == "notifications/initialized" and self._handshake:
                    self._ready = True
                return None
            if data["method"] == "initialize":
                self._handshake = True
                return _result(data["id"], {"protocolVersion": PROTOCOL_VERSION, "capabilities": {"tools": {}}, "serverInfo": SERVER_INFO})
            if not self._handshake:
                return _error(data["id"], -32002, "Not initialized")
            if data["method"] == "tools/list":
                if not self._ready:
                    return _error(data["id"], -32002, "Not ready")
                return _result(data["id"], {"tools": TOOLS})
            if data["method"] == "tools/call":
                if not self._ready:
                    return _error(data["id"], -32002, "Not ready")
                if "name" not in data["params"] or "arguments" not in data["params"]:
                    return _error(data["id"], -32602, "Missing or invalid arguments")
                name = data["params"]["name"]
                arguments = data["params"]["arguments"]
                if "text" not in arguments:
                    return _error(data["id"], -32602, "Missing text")
                chunks = chunk_text(arguments["text"], 
                                    arguments.get("size", 500),
                                    arguments.get("overlap", 50))
                return _result(data["id"], {"content": [{"type": "text", "text": json.dumps(chunks)}], "isError": False})
            return _error(data["id"], -32601, "Unknown method")
        except json.JSONDecodeError:
            return _error(None, -32700, "Invalid JSON")
        except ValueError as e:
            return _error(data["id"], -32602, str(e))


# ------------------------------------------------------------- checks

RESULTS = {}


def check(name, fn):
    try:
        fn()
        RESULTS[name] = "PASS"
    except NotImplementedError:
        RESULTS[name] = "TODO"
    except AssertionError as e:
        RESULTS[name] = f"FAIL ({e})"
    except Exception as e:
        RESULTS[name] = f"FAIL ({type(e).__name__}: {e})"
    print(f"{name}: {RESULTS[name]}")


def req(rid, method, params=None):
    m = {"jsonrpc": "2.0", "id": rid, "method": method}
    if params is not None:
        m["params"] = params
    return json.dumps(m)


def ready_server():
    s = McpServer()
    s.handle_line(req(1, "initialize", {
        "protocolVersion": PROTOCOL_VERSION, "capabilities": {},
        "clientInfo": {"name": "checks", "version": "0"}}))
    s.handle_line(json.dumps({"jsonrpc": "2.0",
                              "method": "notifications/initialized"}))
    return s


def d1():
    out = json.loads(McpServer().handle_line("this is not json"))
    assert out["id"] is None and out["error"]["code"] == -32700, out


def d2():
    out = json.loads(McpServer().handle_line(req(7, "tools/list")))
    assert out["id"] == 7 and out["error"]["code"] == -32002, out


def d3():
    s = McpServer()
    out = json.loads(s.handle_line(req(1, "initialize", {
        "protocolVersion": PROTOCOL_VERSION, "capabilities": {},
        "clientInfo": {"name": "checks", "version": "0"}})))
    r = out["result"]
    assert out["id"] == 1 and r["protocolVersion"] == PROTOCOL_VERSION, out
    assert r["serverInfo"]["name"] == "lab-server", out
    assert "tools" in r["capabilities"], out


def d4():
    s = McpServer()
    n = json.dumps({"jsonrpc": "2.0", "method": "notifications/cancelled"})
    assert s.handle_line(n) is None, "notifications are never answered"
    s2 = ready_server()
    assert s2.handle_line(n) is None


def d5():
    s = McpServer()
    s.handle_line(req(1, "initialize", {
        "protocolVersion": PROTOCOL_VERSION, "capabilities": {},
        "clientInfo": {"name": "checks", "version": "0"}}))
    out = json.loads(s.handle_line(req(2, "tools/list")))
    assert out["error"]["code"] == -32002, f"not ready yet: {out}"
    s = ready_server()
    out = json.loads(s.handle_line(req(3, "tools/list")))
    tools = out["result"]["tools"]
    assert [t["name"] for t in tools] == ["chunk_text"], tools
    assert tools[0]["inputSchema"]["required"] == ["text"], tools


def d6():
    s = ready_server()
    out = json.loads(s.handle_line(req(9, "tools/call", {
        "name": "chunk_text", "arguments": {"text": "x" * 1200}})))
    r = out["result"]
    assert r["isError"] is False, out
    chunks = json.loads(r["content"][0]["text"])
    assert chunks == ["x" * 500, "x" * 500, "x" * 300], \
        [len(c) for c in chunks]


def d7():
    s = ready_server()
    out = json.loads(s.handle_line(req(4, "tools/call", {
        "name": "chunk_text", "arguments": {}})))
    assert out["error"]["code"] == -32602, out
    out = json.loads(s.handle_line(req(5, "tools/call", {
        "name": "nope", "arguments": {}})))
    assert out["error"]["code"] == -32602, out
    out = json.loads(s.handle_line(req(6, "tools/call", {
        "name": "chunk_text",
        "arguments": {"text": "abc", "size": 10, "overlap": 10}})))
    assert out["error"]["code"] == -32602, out


def d8():
    s = ready_server()
    out = json.loads(s.handle_line(req(8, "resources/list")))
    assert out["error"]["code"] == -32601, out


if __name__ == "__main__":
    for name, fn in [("D1 parse error", d1), ("D2 pre-initialize", d2),
                     ("D3 initialize", d3), ("D4 notification silence", d4),
                     ("D5 discovery after ready", d5), ("D6 tools/call", d6),
                     ("D7 bad call params", d7), ("D8 unknown method", d8)]:
        check(name, fn)
    done = sum(1 for v in RESULTS.values() if v == "PASS")
    print(f"\n{done}/8 checks passing")
