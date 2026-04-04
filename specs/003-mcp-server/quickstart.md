# Quickstart: Phase 2D — MCP Server

**Date**: 2026-04-02 | **Branch**: `003-mcp-server`

---

## Prerequisites

```bash
pip install mcp>=1.2.0       # add mcp to requirements.txt first
pip install -r requirements.txt
```

Ensure `.env` exists at project root with:
```
OPENAI_API_KEY=sk-...        # optional: only needed for escalate_to_human AI eval
```

---

## Run the MCP Server (stdio mode)

```bash
# From project root
python -m src.mcp_server.server
```

The server starts and listens on stdin for JSON-RPC messages.
Logs are written to stderr only (stdout is reserved for JSON-RPC).

---

## Register with Claude Code (`.claude.json`)

Add to `.claude.json` in your project root (create if missing):

```json
{
  "mcpServers": {
    "nexaflow-crm": {
      "command": "python",
      "args": ["-m", "src.mcp_server.server"],
      "cwd": "/home/ps_qasim/projects/crm-digital-fte"
    }
  }
}
```

Restart Claude Code after updating this file. The 7 CRM tools will be available in the
tool palette.

---

## Run Unit Tests

```bash
# From project root
pytest tests/unit/mcp_server/ -v

# Full regression (all 52 + new MCP tests)
pytest -v
```

---

## Manual Smoke Test (pipe JSON-RPC)

```bash
# List available tools
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | python -m src.mcp_server.server

# Call search_knowledge_base
echo '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"search_knowledge_base","arguments":{"query":"workflow automation triggers"}}}' | python -m src.mcp_server.server
```

---

## Interactive Inspector (if mcp CLI available)

```bash
mcp dev src/mcp_server/server.py
```

Opens a browser-based inspector to call tools interactively.

---

## Tool Call Order (as per Constitution §IV-2)

When using the MCP server as the agent's tool backend, the required call order is:

```
create_ticket → get_customer_history → search_knowledge_base → send_response
```

`escalate_to_human` replaces `send_response` when escalation is required.
`resolve_ticket` is called after confirming the customer's issue is resolved.
`get_sentiment_trend` can be called before `resolve_ticket` to check for escalation signals.
