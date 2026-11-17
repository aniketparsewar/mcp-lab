# MCP Lab — your stack, speaking the standard protocol

Project 8. In Project 4 you built a private tool protocol: the model
emitted `{"tool": ..., "args": ...}`, your Python dispatched it, results
came back as observations. **MCP (Model Context Protocol) is that idea
as an open standard** — any client can discover and call any server's
tools, resources, and prompts, without custom glue.

This lab re-exposes what you already built through the standard:

| Piece | What it is |
|-------|------------|
| `server/shipdoc_server.py` | Your deployed ShipDocChat RAG service as an **MCP server** (tool + resource + prompt) |
| `server/local_tools_server.py` | Project 4's calculator + sandboxed file tools as an MCP server |
| `client/probe.py` | A minimal **MCP client**: spawn a server over stdio, discover its primitives, call a tool |
| `claude_desktop_config.example.json` | Connect both servers to a real MCP host |

## The three primitives

- **Tools** — model-callable functions (`ask_statement`, `calculator`, ...).
- **Resources** — readable context identified by URI (`shipdocchat://status`).
- **Prompts** — reusable prompt templates (`analyze_statement`).

## Quickstart

```bash
pip install -r requirements.txt
cp .env.example .env   # SHIPDOCCHAT_API_KEY

# Discover what a server offers:
python client/probe.py server/shipdoc_server.py

# Call a tool through the protocol:
python client/probe.py server/shipdoc_server.py --call ask_statement --args "{\"question\": \"What is my new balance?\"}"
python client/probe.py server/local_tools_server.py --call calculator --args "{\"expression\": \"64.99 + 14.99 + 29.95\"}"

# Or explore interactively with the MCP Inspector:
npx @modelcontextprotocol/inspector python server/shipdoc_server.py
```

## Connect a real host

Copy `claude_desktop_config.example.json`, fix the paths, and place it
as your Claude Desktop MCP config, then restart the host. Your two
servers appear as tools the host's model can call — code you wrote,
driven by a client you didn't.

> **Demo data honesty note:** the statement behind ShipDocChat is the
> fictional Nebula Bank sample. Made-up fixture, not real financial data.

## Known demo-grade limits

- stdio transport = local, single-user, trusted. Remote MCP (Day 3)
  needs auth and a threat model — tool descriptions are an attack
  surface (tool poisoning is indirect prompt injection with a badge).
- The ShipDocChat store lives on ephemeral disk; if `ask_statement`
  returns the "No document ingested" error, re-upload the PDF.

## What I learned

- *(fill in after the project closes)*
