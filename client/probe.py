"""Minimal MCP client: spawn a server over stdio, list its primitives, call a tool.

Usage:
  python client/probe.py server/shipdoc_server.py
  python client/probe.py server/shipdoc_server.py --call ask_statement --args "{\\"question\\": \\"What is my new balance?\\"}"
  python client/probe.py server/local_tools_server.py --call calculator --args "{\\"expression\\": \\"64.99 + 14.99 + 29.95\\"}"

This is the client half of the protocol: initialize, discover, call.
Day 2 wires this same pattern into AgentOps.
"""
import argparse
import asyncio
import json
import os
import sys

from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("server", help="path to the server .py file")
    ap.add_argument("--call", help="tool name to call after listing")
    ap.add_argument("--args", default="{}", help="JSON arguments for the call")
    a = ap.parse_args()

    params = StdioServerParameters(
        command=sys.executable, args=[a.server], env=dict(os.environ)
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("TOOLS:")
            for t in tools.tools:
                desc = (t.description or "").splitlines()[0]
                print(f"  - {t.name}: {desc}")
            resources = await session.list_resources()
            if resources.resources:
                print("RESOURCES:", [str(r.uri) for r in resources.resources])
            prompts = await session.list_prompts()
            if prompts.prompts:
                print("PROMPTS:", [p.name for p in prompts.prompts])
            if a.call:
                result = await session.call_tool(a.call, json.loads(a.args))
                print(f"\nCALL {a.call} ->")
                for block in result.content:
                    print(getattr(block, "text", block))


if __name__ == "__main__":
    asyncio.run(main())
