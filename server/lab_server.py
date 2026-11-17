"""Day 1, Part B — the same tool on the SDK (mcp 2.x).

Part A was the wire by hand: framing, handshake, dispatch, error
codes. This file declares the SAME chunk_text tool with the SDK and
lets the framework own all of that. What to notice while you build
it: your function's docstring becomes the tool description a client
shows the model, and your type hints become the inputSchema you
wrote out longhand in Part A's TOOLS table.

Drive it with the parked client (plumbing, given):
  python client/probe.py server/lab_server.py
  python client/probe.py server/lab_server.py --call chunk_text \
      --args '{"text": "aaaa...", "size": 4, "overlap": 1}'
"""
from mcp.server.mcpserver import MCPServer

server = MCPServer("lab-server")


@server.tool()
def chunk_text(text: str, size: int = 500, overlap: int = 50) -> list[str]:
    """Split a document into fixed-size character windows with
    overlap (the W5 fixed chunker, as a tool).

    TODO(you): the same contract as Part A — windows step
    (size - overlap), last window may be short, empty text -> [].
    For invalid size/overlap, raise ValueError and watch what the
    SDK turns it into on the wire (compare with Part A's -32602).
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


if __name__ == "__main__":
    server.run()
