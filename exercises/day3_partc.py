"""Day 3, Part C mechanical checks (the LLM runs are poison_run.py).

    python exercises/day3_partc.py

C1: the rogue server's `add` description carries the payload
    (names secrets.txt and instructs including its contents).
C2: admit_tools keeps a tool whose description matches the pin,
    drops the same tool with a poisoned description, and drops
    tools that were never reviewed.
"""
import hashlib
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from host_policy import admit_tools

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {name} {detail}")


class FakeTool:
    def __init__(self, name, description):
        self.name, self.description = name, description


async def main():
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(ROOT / "server" / "rogue_server.py")],
        env=dict(os.environ),
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = (await session.list_tools()).tools
    add = next(t for t in tools if t.name == "add")
    desc = (add.description or "").lower()
    check("C1 payload present in description",
          "secrets.txt" in desc and ("include" in desc or "contents" in desc),
          f"description starts: {(add.description or '')[:60]!r}")

    clean = "Add two numbers and return the sum."
    approved = {"add": hashlib.sha256(clean.encode("utf-8")).hexdigest()}
    kept, dropped = admit_tools([FakeTool("add", clean)], approved)
    check("C2a clean description kept", [t.name for t in kept] == ["add"] and dropped == [])
    kept, dropped = admit_tools([FakeTool("add", add.description)], approved)
    check("C2b poisoned description dropped", kept == [] and dropped == ["add"])
    kept, dropped = admit_tools([FakeTool("mystery", "anything")], approved)
    check("C2c unreviewed tool dropped", kept == [] and dropped == ["mystery"])

    print(f"\n{sum(RESULTS)}/{len(RESULTS)} checks passed")


if __name__ == "__main__":
    anyio.run(main)
