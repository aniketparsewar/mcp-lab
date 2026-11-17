"""Day 3, Part A: the Day 1 lab server over streamable HTTP.

Same tool, same code — only the transport changes. Run it and LEAVE
IT RUNNING (it is now a standalone service, not your subprocess):

    python server/lab_http_server.py

It listens on http://127.0.0.1:8123/mcp
"""
from mcp.server.mcpserver import MCPServer

server = MCPServer("lab-http")


@server.tool()
def chunk_text(text: str, size: int = 4, overlap: int = 1) -> str:
    """Split text into chunks of size with overlap and join with '/'."""
    if overlap >= size:
        raise ValueError("overlap must be smaller than size")
    step = size - overlap
    return "/".join(text[i:i + size] for i in range(0, len(text), step))


if __name__ == "__main__":
    server.run("streamable-http", port=8123)
