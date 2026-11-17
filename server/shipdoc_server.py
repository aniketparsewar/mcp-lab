"""ShipDocChat as an MCP server.

Wraps the DEPLOYED Project 6 service (https://ship-docchat.onrender.com)
as Model Context Protocol primitives, so any MCP host (Claude Desktop,
the MCP Inspector, your own client) can use your RAG service without
knowing your private HTTP API.

Your Project 4 agent had a private tool protocol: the model emitted
{"tool": ..., "args": ...} and your Python dispatched it. MCP is that
idea as a standard — this file is the same wrapping job, done once,
usable by everyone.

Run (stdio transport):  python server/shipdoc_server.py
"""
import os

import httpx
from dotenv import load_dotenv
#from mcp.server.fastmcp import FastMCP
from mcp.server.mcpserver import MCPServer

load_dotenv()

SHIPDOCCHAT_URL = os.environ.get("SHIPDOCCHAT_URL", "https://ship-docchat.onrender.com").rstrip("/")
SHIPDOCCHAT_API_KEY = os.environ.get("SHIPDOCCHAT_API_KEY", "")

server = MCPServer("shipdocchat")
#mcp = FastMCP("shipdocchat")


@server.tool()
def ask_statement(question: str, top_k: int = 3) -> dict:
    """Ask the credit card statement a question. Returns the answer with
    citations, retrieval scores, refusal flag, and the call's cost."""
    if not SHIPDOCCHAT_API_KEY:
        return {"error": "SHIPDOCCHAT_API_KEY is not set on the server."}
    top_k = max(1, min(int(top_k), 5))
    try:
        resp = httpx.post(
            f"{SHIPDOCCHAT_URL}/ask",
            headers={"X-API-Key": SHIPDOCCHAT_API_KEY, "Content-Type": "application/json"},
            json={"question": question, "top_k": top_k},
            timeout=90.0,
        )
    except httpx.HTTPError as e:
        return {"error": f"ShipDocChat unreachable: {e}"}
    if resp.status_code == 503:
        return {"error": "No document ingested yet - the service's store is empty "
                         "(ephemeral disk). Re-upload the PDF first."}
    if resp.status_code != 200:
        return {"error": f"ShipDocChat returned {resp.status_code}: {resp.text[:200]}"}
    body = resp.json()
    return {
        "answer": body["answer"],
        "citations": body.get("citations", []),
        "chunk_scores": body.get("chunk_scores", []),
        "cost_usd": body.get("cost_usd", 0.0),
        "refused": body.get("refused", False),
    }


@server.resource("shipdocchat://status")
def status() -> str:
    """Health of the deployed ShipDocChat service, as a resource."""
    try:
        resp = httpx.get(f"{SHIPDOCCHAT_URL}/health", timeout=30.0)
        return resp.text
    except httpx.HTTPError as e:
        return f"unreachable: {e}"


@server.prompt()
def analyze_statement(question: str) -> str:
    """Prompt template: answer from the statement and show the evidence."""
    return (
        f"Use the ask_statement tool to answer: {question}\n"
        "Then explain which citations support the answer, and say plainly "
        "if the statement does not contain the answer."
    )


if __name__ == "__main__":
    server.run()  # stdio transport by default
