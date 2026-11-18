"""Day 4: the Day 3 authenticated HTTP server, packaged for deployment.

Same server as lab_http_auth_server.py — chunk_text behind a bearer
token — with deployment-shaped configuration:

- PUBLIC_URL: the server's public base URL (OAuth issuer/resource
  identifiers must name the server as clients know it). On Render
  this falls back to RENDER_EXTERNAL_URL, which Render sets itself.
- LAB_MCP_TOKEN: the shared lab token (set as a platform env var,
  never committed).
- DNS rebinding protection is disabled in build_app(): the SDK
  enables it for localhost development, but a remote server is
  reached under its platform hostname, and the bearer token — not
  the Host header — is this server's access gate.

Local run:  python server/remote_server.py   (uvicorn on :8125)
Deployed:   uvicorn app:app  (see app.py at the project root)
"""
import os

from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings
from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

PUBLIC_URL = (
    os.environ.get("PUBLIC_URL")
    or os.environ.get("RENDER_EXTERNAL_URL")
    or "http://127.0.0.1:8125"
)
EXPECTED = os.environ.get("LAB_MCP_TOKEN", "lab-secret-token")


class StaticTokenVerifier:
    async def verify_token(self, token: str) -> AccessToken | None:
        if token == EXPECTED:
            return AccessToken(token=token, client_id="remote-client", scopes=["tools"])
        return None


server = MCPServer(
    "lab-remote",
    token_verifier=StaticTokenVerifier(),
    auth=AuthSettings(
        issuer_url=PUBLIC_URL,
        resource_server_url=PUBLIC_URL,
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


def build_app():
    return server.streamable_http_app(
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=False
        ),
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(build_app(), host="127.0.0.1", port=8125)
