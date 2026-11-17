"""MCP Lab Day 3 — streamable HTTP + auth. Exercises with self-checks.

BEFORE RUNNING: start both servers, each in its own terminal, and
leave them running:
    python server/lab_http_server.py        (port 8123, no auth)
    python server/lab_http_auth_server.py   (port 8124, token auth)

Then:  python exercises/day3.py

Part A TODO (call_chunk): the client side of the new transport.
Part B has no code here — its TODO is the verifier in
server/lab_http_auth_server.py; these checks grade it over the wire.
"""
import os

import anyio
import httpx2
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

TOKEN = os.environ.get("LAB_MCP_TOKEN", "lab-secret-token")
PLAIN_URL = "http://127.0.0.1:8123/mcp"
AUTH_URL = "http://127.0.0.1:8124/mcp"

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {name} {detail}")


async def call_chunk(url, token=None):
    """Connect to an MCP server over streamable HTTP, initialize,
    list tools, call chunk_text('abcdefghij', 4, 1).
    Returns (tool_names, result_text).

    TODO (yours) — the new mechanism is the transport constructor:
      headers = {"Authorization": f"Bearer {token}"} if token else {}
      http_client = httpx2.AsyncClient(headers=headers)
      async with streamable_http_client(url, http_client=http_client) as (read, write):
          async with ClientSession(read, write) as session:
              ... initialize, list_tools, call_tool ...
    Note the 2.x client yields TWO streams, not three.
    """
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    http_client = httpx2.AsyncClient(headers=headers)
    async with http_client:
        async with streamable_http_client(url, http_client=http_client) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                listing = await session.list_tools()
                names = [t.name for t in listing.tools]
                result = await session.call_tool(
                    "chunk_text",
                    {"text": "abcdefghij", "size": 4, "overlap": 1},
                )
                out = result.content[0].text if result.content else ""
                return names, out


async def main():
    # ---- Part A: HTTP transport -------------------------------------
    names, out = await call_chunk(PLAIN_URL)
    check("A1 http tools+call", names == ["chunk_text"] and out == "abcd/defg/ghij/j", out)
    # A second client against the SAME already-running server process.
    # (With stdio this was impossible: every client spawned its own.)
    names2, out2 = await call_chunk(PLAIN_URL)
    check("A2 second client, same server", names2 == names and out2 == out)

    # ---- Part B: auth ------------------------------------------------
    try:
        await call_chunk(AUTH_URL)
        check("B1 no token rejected", False, "call succeeded without a token")
    except Exception as e:
        check("B1 no token rejected", True, type(e).__name__)
    try:
        await call_chunk(AUTH_URL, token="wrong-token")
        check("B2 wrong token rejected", False, "call succeeded with a wrong token")
    except Exception as e:
        check("B2 wrong token rejected", True, type(e).__name__)
    names3, out3 = await call_chunk(AUTH_URL, token=TOKEN)
    check("B3 right token works", out3 == "abcd/defg/ghij/j", out3)

    print(f"\n{sum(RESULTS)}/{len(RESULTS)} checks passed")


if __name__ == "__main__":
    anyio.run(main)
