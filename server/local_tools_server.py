"""Calculator + sandboxed file tools as an MCP server. (Tools from Project 4.)

The same three tools your agent used through its private protocol,
re-exposed through the standard one. Two servers, one client — that
composability is the point of MCP.

Run (stdio transport):  python server/local_tools_server.py
"""
import ast
import operator
from pathlib import Path

#from mcp.server.fastmcp import FastMCP
from mcp.server.mcpserver import MCPServer
server = MCPServer("local-tools")

#mcp = FastMCP("local-tools")

WORKSPACE = Path("./workspace_files")
WORKSPACE.mkdir(parents=True, exist_ok=True)

_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub,
    ast.Mult: operator.mul, ast.Div: operator.truediv,
    ast.Pow: operator.pow, ast.USub: operator.neg, ast.UAdd: operator.pos,
    ast.Mod: operator.mod,
}


@server.tool()
def calculator(expression: str) -> float:
    """Evaluate a safe arithmetic expression, e.g. '3842.17 - 64.99'."""
    tree = ast.parse(expression, mode="eval")

    def ev(node):
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](ev(node.left), ev(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](ev(node.operand))
        raise ValueError("unsafe expression")

    return ev(tree)


def _safe(name: str) -> Path:
    base = WORKSPACE.resolve()
    p = (base / name).resolve()
    if base != p and base not in p.parents:
        raise ValueError("path escapes workspace")
    return p


@server.tool()
def read_file(name: str) -> str:
    """Read a file from the sandboxed workspace."""
    return _safe(name).read_text(encoding="utf-8")


@server.tool()
def write_file(name: str, content: str) -> str:
    """Write a file into the sandboxed workspace. Never overwrite, clear,
    or delete existing file contents without asking the user first."""
    p = _safe(name)
    p.write_text(content, encoding="utf-8")
    return f"wrote {len(content)} chars to {name}"


if __name__ == "__main__":
    server.run()  # stdio transport by default
