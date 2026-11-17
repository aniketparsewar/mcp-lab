# MCP Lab — project brief (Project 8)

**Why this project exists:** the original curriculum (Projects 1–6 +
AgentOps capstone) predates MCP becoming the standard tool protocol.
Aniket flagged the gap on 2026-10-26; MCP is named in the agentic-AI
platform PM roles he's targeting, and his Project 4 loop was already a
private version of the same idea.

**Thesis:** you don't learn a protocol by reading its spec — you learn
it by re-implementing something you already own in it, then breaking it.

## Provenance

| Piece | From | Adapted how |
|-------|------|-------------|
| `ask_statement` tool | Project 6 (deployed ShipDocChat) | same HTTP call as AgentOps' tool, wrapped in FastMCP |
| `calculator`, `read_file`, `write_file` | Project 4 | same code, standard protocol |
| Client pattern | new | stdio client: initialize → discover → call |

## Day plan (Aniket controls the pace — no next day until he says so)

- **Day 1 — servers + discovery.** Probe both servers; list the three
  primitives; call `ask_statement` through the protocol; connect a real
  host (Inspector or Claude Desktop) and watch a foreign client drive
  your code. Quiz.
- **Day 2 — AgentOps speaks MCP.** Replace AgentOps' private
  `{"tool", "args"}` dispatch with an MCP client connected to both
  servers. The watcher doesn't care how tools are called — verify
  pass_rate is unchanged. That indifference is the protocol's value.
  Quiz.
- **Day 3 — remote MCP + security.** Streamable HTTP transport; auth;
  tool poisoning (a malicious tool description is indirect prompt
  injection — the capstone's Day 3 finding, standardized); why stdio's
  trust model doesn't survive the network. Quiz.
- **Day 4 — deploy.** Remote server live, one real user through a real
  host, README "What I learned". Closing quiz.

## Open questions for later days

- Sampling and elicitation (server asking the *client's* model/user for
  help) — when are they worth the complexity?
- How do you version and test MCP servers? (The watcher idea, applied
  to protocol surface.)
- Tool descriptions as prompts: who reviews them, and how do you eval
  a server you don't control?
