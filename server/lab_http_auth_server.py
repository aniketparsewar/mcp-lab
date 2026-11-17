"""Day 3, Part B: the same HTTP server, now requiring a bearer token.

    set LAB_MCP_TOKEN=lab-secret-token   (Windows: set, or $env: in PS)
    python server/lab_http_auth_server.py

Listens on http://127.0.0.1:8124/mcp

YOUR TODO is StaticTokenVerifier.verify_token below. The plumbing
(AuthSettings, the constructor wiring) is given. Production MCP auth
is OAuth 2.1; a static bearer token is the lab-scale stand-in that
shows WHERE verification lives: in the transport layer, checked
before any protocol message is processed.
"""
import os

from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings
from mcp.server.mcpserver import MCPServer

EXPECTED = os.environ.get("LAB_MCP_TOKEN", "lab-secret-token")


class StaticTokenVerifier:
    async def verify_token(self, token: str) -> AccessToken | None:
        # TODO (yours): if `token` matches EXPECTED, return
        # AccessToken(token=token, client_id="lab-client",
        #             scopes=["tools"])
        # otherwise return None (the SDK turns None into a 401).

        if token == EXPECTED:
            return AccessToken(token=token, client_id="lab-client", scopes=["tools"])
        else:
            return None


server = MCPServer(
    "lab-http-auth",
    token_verifier=StaticTokenVerifier(),
    auth=AuthSettings(
        issuer_url="http://127.0.0.1:8124",
        resource_server_url="http://127.0.0.1:8124",
        required_scopes=["tools"],
    ),
)


@server.tool()
def chunk_text(text: str, size: int = 4, overlap: int = 1) -> str:
    """Split text into chunks of size with overlap and join with '/'."""
    if overlap >= size:
        raise ValueError("overlap must be smaller than size")
    step = size - overlap
    return "/".join(text[i:i + size] for i in range(0, len(text), step))


if __name__ == "__main__":
    server.run("streamable-http", port=8124)
