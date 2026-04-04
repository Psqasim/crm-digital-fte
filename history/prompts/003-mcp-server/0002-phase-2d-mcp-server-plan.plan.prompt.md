---
id: "0002"
title: Phase 2D MCP server plan
stage: plan
date: 2026-04-02
surface: agent
model: claude-sonnet-4-6
feature: 003-mcp-server
branch: 003-mcp-server
user: Muhammad Qasim
command: /sp.plan
labels: ["mcp", "planning", "fastmcp", "stdio", "tool-gateway"]
links:
  spec: specs/003-mcp-server/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/003-mcp-server/plan.md
  - specs/003-mcp-server/research.md
  - specs/003-mcp-server/data-model.md
  - specs/003-mcp-server/quickstart.md
  - specs/003-mcp-server/contracts/tool_schemas.md
tests:
  - none (planning phase — tests specified in plan.md Test Strategy section)
---

## Prompt

 ## CONTEXT
Project: CRM Digital FTE Factory — GIAIC Hackathon 5
Location: /home/ps_qasim/projects/crm-digital-fte
Branch: 003-mcp-server
Phase: 2D — MCP Server

Spec: specs/003-mcp-server/spec.md (7 tools, 14/14 checklist pass)
Existing code the MCP server wraps:
- src/agent/knowledge_base.py
- src/agent/conversation_store.py
- src/agent/escalation_evaluator.py
- src/agent/prototype.py

## TASK
Run /sp.plan for Phase 2D.

Use Context7 MCP to look up current MCP Python SDK docs before planning.
Search for: "mcp python sdk server tools fastmcp"

Plan must cover:
- MCP server file at src/mcp_server/server.py
- Tool registration for all 7 tools
- How each tool calls into existing prototype modules
  (no business logic in MCP layer — thin wrapper only)
- Server transport: stdio (standard for Claude Code MCP integration)
- Error handling per tool (each tool must return error string, never raise)
- Port/conflict check — MCP server must not conflict with any future
  FastAPI port (FastAPI will use 8000, MCP stdio has no port)
- Test strategy: how to test MCP tools without a full MCP client

## RULES
- Work in /home/ps_qasim/projects/crm-digital-fte
- Planning only — no code yet
- Commit when done, do NOT push

## WHEN DONE
Confirm: plan file path + task count. Ready for sp.tasks: yes/no

## Response snapshot

Completed Phase 2D implementation plan. Key decisions:

1. **FastMCP pattern**: `from mcp.server.fastmcp import FastMCP` with `@mcp.tool()` decorator.
   `mcp.run(transport="stdio")` — no port, zero conflict with FastAPI on 8000.

2. **7 tools mapped to existing modules**:
   - `search_knowledge_base` → `KnowledgeBase.search()`
   - `create_ticket` → `store.get_or_create_customer()` + `store.get_or_create_conversation()`
   - `get_customer_history` → `store.get_customer()` + conversation iteration
   - `escalate_to_human` → `store.transition_ticket(ESCALATED)`
   - `send_response` → `store.add_message()` (simulated delivery)
   - `get_sentiment_trend` → `store.compute_sentiment_trend()`
   - `resolve_ticket` → `store.transition_ticket(RESOLVED)`

3. **Ticket index adapter**: `_ticket_index: dict[str, str]` in server.py bridges MCP's
   public `ticket_id` to ConversationStore's internal `conversation_id`. Zero modification to
   Phase 2C code.

4. **Error handling**: All tools catch `Exception`, return `json.dumps({"error":..., "tool":...})`.
   Never raise. Validation errors returned early before try block.

5. **Test strategy**: Direct-import of tool coroutines in pytest; `reset_store()` for isolation.
   ~21 test functions covering all 7 tools × happy path + error cases.

6. **Artifacts**: plan.md, research.md, data-model.md, contracts/tool_schemas.md, quickstart.md

## Outcome

- ✅ Impact: Complete Phase 2D plan with 5 artifacts; ready for sp.tasks
- 🧪 Tests: Test strategy defined — ~21 test functions specified in plan.md
- 📁 Files: 5 planning artifacts created under specs/003-mcp-server/
- 🔁 Next prompts: /sp.tasks for Phase 2D
- 🧠 Reflection: ConversationStore ticket index gap identified and resolved via thin adapter dict in server layer — clean solution that preserves Phase 2C module integrity

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): constitution check PASS (all 7 principles evaluated)
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): run /sp.tasks to generate implementation task list
