# Research: Phase 2D — MCP Server

**Date**: 2026-04-02 | **Branch**: `003-mcp-server`

---

## MCP Python SDK — Key Findings

### Decision: FastMCP (`mcp.server.fastmcp.FastMCP`)

**Rationale**: FastMCP 1.0 was incorporated into the official `mcp` Python SDK. It auto-generates
tool schemas from Python type hints and docstrings. Using `@mcp.tool()` decorator is the
recommended pattern for new servers.

**Pattern (confirmed from modelcontextprotocol.io docs)**:

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("server-name")

@mcp.tool()
async def my_tool(param: str) -> str:
    """Human-readable description for the AI client.

    Args:
        param: What this parameter means.
    """
    return "result"

def main():
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()
```

**Alternatives considered**: Low-level `mcp.server.Server` with manual `ListToolsResult` /
`CallToolResult` builders — requires significantly more boilerplate for the same outcome.
Rejected.

---

### Decision: stdio transport

**Rationale**: Confirmed by MCP official docs and Claude Code MCP integration pattern.
`mcp.run(transport="stdio")` is the standard for local Claude Desktop / Claude Code use.
No port is allocated — zero conflict with future FastAPI on port 8000.

---

### Decision: No stdout in stdio server

**Source**: MCP official documentation — "For STDIO-based servers: Never write to stdout.
Writing to stdout will corrupt the JSON-RPC messages and break your server."

**Implementation rule**: All logging in `server.py` uses:
```python
import logging
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
```
`print()` statements are prohibited in the server module.

---

### Decision: Return `str` from all tools (JSON-serialised)

**Rationale**: FastMCP maps `str` return types to `TextContent` in the MCP protocol. This is
the simplest, fully spec-compliant approach. All tool results are serialised with `json.dumps()`.

Error shape (consistent across all tools):
```json
{"error": "<human-readable message>", "tool": "<tool_name>"}
```

Success shapes: per-tool (see `contracts/tool_schemas.md`).

---

### Decision: Ticket index adapter (`_ticket_index: dict[str, str]`)

**Problem**: `ConversationStore` operates via `conversation_id` for all state mutations.
The MCP spec exposes `ticket_id` as the public handle (matching hackathon rubric language).

**Solution**: `server.py` maintains a module-level dict:
```python
_ticket_index: dict[str, str] = {}  # ticket_id → conversation_id
```
Populated on every `create_ticket` call. Looked up on `escalate_to_human`, `send_response`,
`resolve_ticket`. NOT added to `ConversationStore` (zero modification to Phase 2C code).

**Lifetime**: Process-local (same as ConversationStore — both reset on server restart).

---

### Decision: Direct-import test strategy

**Rationale**: `@mcp.tool()` decorates functions but does not hide them. The decorated function
remains a callable coroutine:
```python
# In test:
from src.mcp_server.server import search_knowledge_base, create_ticket
result = asyncio.run(search_knowledge_base("workflow automation"))
```
No MCP client subprocess needed for unit tests. `reset_store()` from `conversation_store.py`
provides hermetic test isolation.

**Manual smoke testing**: `mcp dev src/mcp_server/server.py` (if mcp CLI installed) or
pipe JSON-RPC to `python -m src.mcp_server.server` via stdin.

---

### Decision: OpenAI key absence handling

**Spec edge case**: "What happens when the OpenAI API key is missing at server start?"

**Decision**: Server starts unconditionally. `escalate_to_human` checks for key presence:
- If key present: calls `evaluate_escalation()` for intent verification, then escalates.
- If key absent: escalates unconditionally (treats caller's request as authoritative).
- Returns descriptive config error if escalation itself fails.

All other 6 tools have zero OpenAI dependency — they operate purely on in-memory store.

---

### MCP Package Version

**Required**: `mcp>=1.2.0` (per official docs minimum for FastMCP + tool decorator pattern).  
**Install**: `pip install mcp` (adds to `requirements.txt`).  
**Import path**: `from mcp.server.fastmcp import FastMCP`
