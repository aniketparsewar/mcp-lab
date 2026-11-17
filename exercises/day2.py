"""MCP Lab Day 2 — a synchronous MCP bridge for AgentOps.

AgentOps' agent loop is synchronous and speaks a private protocol:
_dispatch(name, args) returns plain Python values, and exceptions
become "TOOL ERROR:" observations. MCP clients are async and return
CallToolResult objects. The bridge is the anti-corruption layer between
them: AgentOps keeps its contract; the bridge owns everything MCP.

The plumbing (event loop on a background thread, subprocess/session
lifecycle) is GIVEN. You implement the three mechanisms:

  1. _register  — build the routing table from discovery: which server
     session owns which tool. Two servers, four tools, one namespace.
  2. _call_async — translate the public name (NAME_MAP), route to the
     owning session, call the tool, convert the result.
  3. _convert   — CallToolResult -> the exact shapes AgentOps'
     _dispatch used to return:
       calculator      -> {"result": <float>}
       read_file       -> {"content": <str>}
       write_file      -> {"ok": <str>}
       shipdocchat_ask -> the dict itself
     Conversion rules (measured against the real SDK, not assumed):
       - result.is_error is True -> raise RuntimeError with the text.
       - structured_content == {"result": v} -> the value is v, typed.
       - otherwise the first text block holds it: JSON text for dict
         returns (parse it), or a plain string.
     Server error DICTS ({"error": ...} returned normally, is_error
     False) pass through untouched — they are data, not failures.

Checks: python exercises/day2.py  (run from the mcp-lab root; spawns
the two real servers over stdio)
"""
import asyncio
import json
import os
import sys
import threading
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import get_default_environment, stdio_client

# AgentOps' model-facing name -> the MCP server's name. The model's
# contract (the SYSTEM prompt) does not change; the bridge translates.
NAME_MAP = {"shipdocchat_ask": "ask_statement"}


class McpBridge:
    def __init__(self, servers: dict[str, str]):
        """servers: label -> path of the server .py file."""
        self._servers = servers
        self._sessions: dict[str, ClientSession] = {}  # label -> session
        self._routing: dict[str, str] = {}             # MCP tool name -> label
        self._tools: list[dict] = []                   # discovered tools
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._stack: AsyncExitStack | None = None
        self._ready = threading.Event()

    # ---------- plumbing (given) ----------

    def start(self, timeout: float = 60.0) -> None:
        def run_loop() -> None:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(self._connect())
            self._ready.set()
            self._loop.run_forever()

        self._thread = threading.Thread(target=run_loop, daemon=True)
        self._thread.start()
        if not self._ready.wait(timeout):
            raise RuntimeError("bridge failed to connect in time")

    async def _connect(self) -> None:
        self._stack = AsyncExitStack()
        env = get_default_environment()
        if os.environ.get("PYTHONPATH"):
            env["PYTHONPATH"] = os.environ["PYTHONPATH"]
        for label, path in self._servers.items():
            params = StdioServerParameters(
                command=sys.executable, args=[path], env=env
            )
            read, write = await self._stack.enter_async_context(
                stdio_client(params)
            )
            session = await self._stack.enter_async_context(
                ClientSession(read, write)
            )
            await session.initialize()
            self._sessions[label] = session
            listing = await session.list_tools()
            self._register(label, listing.tools)

    def tool_names(self) -> list[str]:
        return [t["name"] for t in self._tools]

    def call(self, name: str, args: dict, timeout: float = 120.0):
        if self._loop is None:
            raise RuntimeError("bridge not started")
        fut = asyncio.run_coroutine_threadsafe(
            self._call_async(name, args), self._loop
        )
        return fut.result(timeout)

    def close(self) -> None:
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._loop.stop)

    # ---------- TODO 1: discovery -> routing ----------

    def _register(self, label: str, tools: list) -> None:
        """Record each discovered tool: append {"name", "description"}
        to self._tools and map tool name -> label in self._routing.
        (tools are the SDK's Tool objects: .name, .description.)"""
        for tool in tools:
            self._tools.append({"name": tool.name, "description": tool.description})
            self._routing[tool.name] = label
        print(self._tools)


    # ---------- TODO 2: route + call ----------

    async def _call_async(self, name: str, args: dict):
        """Translate the public name via NAME_MAP (names not in the map
        pass through unchanged). Look the MCP name up in the routing
        table — unknown tool: raise ValueError BEFORE any server call.
        Call session.call_tool(mcp_name, args) on the owning session,
        then return self._convert(name, result)."""
        mcp_name = NAME_MAP.get(name, name)
        if mcp_name not in self._routing:
            raise ValueError(f"Unknown tool: {name}")
        session = self._sessions[self._routing[mcp_name]]
        result = await session.call_tool(mcp_name, args)
        return self._convert(name, result)

    # ---------- TODO 3: result conversion ----------

    def _convert(self, public_name: str, result):
        """ CallToolResult → AgentOps' old shapes, using the rules I measured from the real SDK (in the file's docstring): 
        is_error → raise; structured_content {"result": v} → typed value; dict returns arrive as JSON text with no structured content → 
        parse; a server's graceful {"error": ...} dict is data, passed through untouched — only is_error raises."""
        """ is_error → RuntimeError(content[0].text); structured → unwrap ["result"]; else json.loads with a raw-string fallback; 
        then shape by public name (calculator/read_file/write_file wrappers; shipdoc passes its dict through).
        """
        texts = [getattr(b, "text", "") for b in result.content]
        if result.is_error:
            raise RuntimeError(texts[0] if texts else "tool error")
        sc = result.structured_content
        if isinstance(sc, dict) and "result" in sc:
            value = sc["result"]
        else:
            text = texts[0] if texts else ""
            try:
                value = json.loads(text)
            except (json.JSONDecodeError, TypeError):
                value = text
        if public_name == "calculator":
            return {"result": value}
        if public_name == "read_file":
            return {"content": value}
        if public_name == "write_file":
            return {"ok": value}
        return value

# ---------------------------------------------------------------------
# Checks — real servers, real stdio, no mocks.
# ---------------------------------------------------------------------

def run_checks() -> None:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root)
    bridge = McpBridge({
        "local": "server/local_tools_server.py",
        "shipdoc": "server/shipdoc_server.py",
    })
    bridge.start()
    passed = failed = 0

    def check(label, fn):
        nonlocal passed, failed
        try:
            fn()
            passed += 1
            print(f"{label}: PASS")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"{label}: FAIL ({type(e).__name__}: {e})")

    def e1():
        names = sorted(bridge.tool_names())
        assert names == ["ask_statement", "calculator", "read_file",
                         "write_file"], names

    def e2():
        out = bridge.call("calculator", {"expression": "3842.17 - 64.99"})
        assert isinstance(out, dict) and "result" in out, out
        assert abs(out["result"] - 3777.18) < 0.01, out

    def e3():
        w = bridge.call("write_file", {"name": "bridge_test.txt",
                                       "content": "hello"})
        assert w == {"ok": "wrote 5 chars to bridge_test.txt"}, w
        r = bridge.call("read_file", {"name": "bridge_test.txt"})
        assert r == {"content": "hello"}, r

    def e4():
        out = bridge.call("shipdocchat_ask", {"question": "balance?"})
        assert isinstance(out, dict), type(out)
        assert "error" in out or "answer" in out, out

    def e5():
        try:
            bridge.call("calculator", {"expression": "__import__('os')"})
        except RuntimeError:
            return
        raise AssertionError("is_error result did not raise")

    def e6():
        try:
            bridge.call("nope", {})
        except ValueError:
            return
        raise AssertionError("unknown tool did not raise ValueError")

    check("E1 discovery across both servers", e1)
    check("E2 calculator in AgentOps shape", e2)
    check("E3 write/read round trip", e3)
    check("E4 name map + error dict passthrough", e4)
    check("E5 is_error raises RuntimeError", e5)
    check("E6 unknown tool raises ValueError", e6)
    bridge.close()
    print(f"\n{passed}/6 checks passing")


if __name__ == "__main__":
    run_checks()
