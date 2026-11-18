"""Day 4 verification: point the Day 3 client checks at the PUBLIC URL.

    set REMOTE_URL=https://<your-service>.onrender.com
    set LAB_MCP_TOKEN=<the token you set on Render>
    python scripts/remote_check.py

Expects: no token -> rejected, wrong token -> rejected,
right token -> tools listed and chunk_text answers abcd/defg/ghij/j.
"""
import os

import anyio
import httpx2
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


BASE = os.environ.get("REMOTE_URL", "").rstrip("/")
#BASE = os.environ.get("REMOTE_URL", "http://127.0.0.1:8125").rstrip("/")
TOKEN = os.environ.get("LAB_MCP_TOKEN", "lab-secret-token")
URL = f"{BASE}/mcp"

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {name} {detail}")


async def probe(token=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with streamable_http_client(URL, http_client=httpx2.AsyncClient(headers=headers)) as (read, write):
        async with ClientSession(read, write) as s:
            await s.initialize()
            tools = await s.list_tools()
            res = await s.call_tool("chunk_text", {"text": "abcdefghij", "size": 4, "overlap": 1})
            return [t.name for t in tools.tools], res.content[0].text


async def main():
    assert BASE, "set REMOTE_URL to your deployed base URL first"
    try:
        await probe()
        check("R1 no token rejected", False, "succeeded without a token")
    except Exception as e:
        check("R1 no token rejected", True, type(e).__name__)
    try:
        await probe("wrong-token")
        check("R2 wrong token rejected", False, "succeeded with a wrong token")
    except Exception as e:
        check("R2 wrong token rejected", True, type(e).__name__)
    names, out = await probe(TOKEN)
    check("R3 right token works", names == ["chunk_text"] and out == "abcd/defg/ghij/j", out)
    print(f"\n{sum(RESULTS)}/{len(RESULTS)} checks passed")


if __name__ == "__main__":
    anyio.run(main)
