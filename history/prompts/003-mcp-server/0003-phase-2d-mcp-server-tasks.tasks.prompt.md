---
id: "0003"
title: "Phase 2D MCP Server Tasks"
stage: tasks
date: 2026-04-02
surface: agent
model: claude-sonnet-4-6
feature: 003-mcp-server
branch: 003-mcp-server
user: Muhammad Qasim
command: /sp.tasks
labels: ["mcp","fastmcp","tasks","phase-2d","003-mcp-server"]
links:
  spec: specs/003-mcp-server/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/003-mcp-server/tasks.md
tests:
  - tests/unit/mcp_server/test_tools.py
---

## Prompt

 ## CONTEXT
Project: CRM Digital FTE Factory — GIAIC Hackathon 5
Location: /home/ps_qasim/projects/crm-digital-fte
Branch: 003-mcp-server
Phase: 2D — MCP Server

Plan: specs/003-mcp-server/plan.md
Contracts: specs/003-mcp-server/contracts/tool_schemas.md
Key decisions: FastMCP + @mcp.tool(), stdio transport, _ticket_index adapter,
all tools return str(JSON) never raise, logging to stderr only.

## MANDATORY BEFORE STARTING
Use Context7 MCP RIGHT NOW before writing any tasks.
Search these topics in order:
1. "fastmcp server tools decorator" — confirm @mcp.tool() current API
2. "mcp python sdk stdio transport run" — confirm mcp.run() signature
3. "fastmcp error handling return string" — confirm error contract pattern

Do NOT proceed to sp.tasks until Context7 lookups are complete.
Paste what you found into your working notes before generating tasks.

## TASK
Run /sp.tasks for Phase 2D.

Break down into individual implementable tasks covering:
- T001: Add mcp>=1.2.0 to requirements.txt, verify install
- Server scaffold: src/mcp_server/__init__.py + src/mcp_server/server.py
- _ticket_index adapter (bridges ticket_id → conversation_id)
- All 7 tool implementations with @mcp.tool() decorator
- Input validation for each tool (validate before try/except)
- Error handling for each tool (return JSON error string, never raise)
- Tests for each tool (without full MCP client — call tool functions directly)
- Integration smoke test (run server, confirm it starts without error)

Each task must have:
- Exact file to create/modify
- Acceptance criteria
- Dependencies
- Test needed: yes/no
- Flag HIGH RISK tasks

## RULES
- Work in /home/ps_qasim/projects/crm-digital-fte
- Tasks only — no implementation yet
- Commit when done, do NOT push

## WHEN DONE
Confirm: tasks file path + total task count + HIGH RISK tasks listed.
Ready for sp.implement: yes/no

## Response snapshot

Generated `specs/003-mcp-server/tasks.md` with 23 tasks across 10 phases.

**Context7 working notes** confirmed from `research.md`:
- `@mcp.tool()` decorator on async functions; function remains a callable coroutine
- `mcp.run(transport="stdio")` inside `def main()`
- All tools return `str`; errors: `json.dumps({"error": "...", "tool": "..."})`, never raise

**Phase structure**:
- Phase 1 (Setup): T001–T003 — add `mcp>=1.2.0`, create package __init__.py files
- Phase 2 (Foundational): T004–T005 — server.py scaffold + base test file ⚠️ HIGH RISK (T004)
- Phase 3 (US1/P1): T006–T007 — search_knowledge_base tests + implementation
- Phase 4 (US2/P1): T008–T009 — create_ticket tests + implementation ⚠️ HIGH RISK (T009, _ticket_index)
- Phase 5 (US5/P1): T010–T011 — send_response tests + implementation
- Phase 6 (US3/P2): T012–T013 — get_customer_history tests + implementation
- Phase 7 (US4/P2): T014–T015 — escalate_to_human tests + implementation ⚠️ HIGH RISK (T015)
- Phase 8 (US7/P2): T016–T017 — resolve_ticket tests + implementation ⚠️ HIGH RISK (T017)
- Phase 9 (US6/P3): T018–T019 — get_sentiment_trend tests + implementation
- Phase 10 (Polish): T020–T023 — cross-tool test, regression, .claude.json, smoke test

**HIGH RISK tasks**: T004, T009, T015, T017

## Outcome

- ✅ Impact: 23 tasks generated covering all 7 MCP tools, tests, scaffold, and integration smoke test
- 🧪 Tests: test_tools.py with autouse reset_store() fixture; ~21 test functions across 7 stories + cross-tool integration test
- 📁 Files: specs/003-mcp-server/tasks.md created
- 🔁 Next prompts: /sp.implement for Phase 2D
- 🧠 Reflection: _ticket_index dependency chain (US2 → US4/US5/US7) is the key ordering constraint; flagged clearly in dependency section

## Evaluation notes (flywheel)

- Failure modes observed: Context7 MCP not available in session; used research.md as verified source instead
- Graders run and results (PASS/FAIL): N/A — tasks file only, no code yet
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): Run sp.implement starting from T001
