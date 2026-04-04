---
id: "0004"
title: Phase 4B Production Agent Tasks
stage: tasks
date: 2026-04-04
surface: agent
model: claude-sonnet-4-6
feature: 006-production-agent
branch: 006-production-agent
user: Muhammad Qasim
command: /sp.tasks
labels: ["tasks","phase-4b","production-agent","tools","openai-agents-sdk","high-risk"]
links:
  spec: specs/006-production-agent/spec.md
  ticket: null
  adr: history/adr/ADR-0003-pydantic-basemodel-vs-typeddict.md
  pr: null
files:
  - specs/006-production-agent/tasks.md
tests:
  - production/tests/test_agent_tools.py (to be created in T004)
  - production/tests/test_agent_integration.py (to be created in T024)
---

## Prompt

## CONTEXT
Project: CRM Digital FTE Factory — GIAIC Hackathon 5
Location: /home/ps_qasim/projects/crm-digital-fte
Branch: 006-production-agent
Phase: 4B — OpenAI Agents SDK Agent

Plan: specs/006-production-agent/plan.md (7 tasks T-001 to T-007)
HIGH RISK: T-004 (tools.py async pool + embeddings), T-005 (agent + retry logic)
ADR-0003: Pydantic BaseModel for 5 tools, Annotated primitives for 2
Recommended order: T-001→T-002→T-003→T-006→T-004→T-005→T-007
DB queries: production/database/queries.py (13 async functions, injectable pool)
Prototype to port: src/agent/prompts.py, src/agent/channel_formatter.py
Current passing tests: 101/101

## TASK
Run /sp.tasks for Phase 4B.

Break all 7 plan tasks into individual implementable units.
Follow recommended order: T-001→T-002→T-003→T-006→T-004→T-005→T-007

Each task must have:
- Exact file to create/modify
- Acceptance criteria
- Dependencies
- Test needed: yes/no
- HIGH RISK flag if applicable

Special notes per task:

**T-004 (tools.py) — HIGH RISK subtasks:**
Break into 7 sub-tasks, one per tool:
- T-004a: search_knowledge_base (needs embedding call + vector search)
- T-004b: create_ticket (needs get_or_create_customer first)
- T-004c: get_customer_history
- T-004d: escalate_to_human (state transition guard)
- T-004e: send_response (stub — channel dispatch in 4C)
- T-004f: get_sentiment_trend
- T-004g: resolve_ticket (idempotency guard — same pattern as Phase 2D)
Each sub-task: pytest after implementing, must not break 101 existing tests

**T-005 (customer_success_agent.py) — HIGH RISK subtasks:**
- T-005a: Agent definition (name, instructions callable with datetime injection, tools list, model=gpt-4o-mini)
- T-005b: Runner wrapper with retry (APIError → retry once → escalate)
- T-005c: RunResult parser (final_output str → AgentResponse dataclass)
- T-005d: Channel-aware instructions (email/whatsapp/web_form tone injection)

**T-007 (integration tests):**
Must test:
- Full agent run with mocked DB pool (no real Neon needed)
- Tool call ordering (create_ticket before send_response)
- Retry logic on APIError
- Channel-appropriate response format per channel
- Escalation path (agent calls escalate_to_human correctly)

## RULES
- Work in /home/ps_qasim/projects/crm-digital-fte
- Tasks breakdown only — no implementation yet
- Commit when done, do NOT push

## WHEN DONE
Confirm: tasks file path + total subtask count + all HIGH RISK subtasks listed.
Ready for sp.implement: yes/no

## Response snapshot

Generated `specs/006-production-agent/tasks.md` with 29 tasks across 6 phases:

- **Phase 2 (Foundational)**: T001–T003 — schemas.py, prompts.py, formatters.py (pure Python, parallelisable)
- **Phase 3 (US1 MVP)**: T004–T018 — unit test scaffold + all 5 US1 tools + agent dataclasses + Agent def + Runner retry + RunResult parser
- **Phase 4 (US2)**: T019 — channel-aware instructions wire-in
- **Phase 5 (US3)**: T020–T023 — escalate_to_human + get_sentiment_trend tools + unit tests
- **Phase 6 (Integration)**: T024–T029 — test_agent_integration.py scaffold + 5 integration test classes (parallel)

12 HIGH RISK subtasks: T005, T007, T009, T011, T013, T015, T016, T017, T018, T019, T020, T022

## Outcome

- ✅ Impact: tasks.md generated — 29 tasks, all 7 plan tasks decomposed, implementation-ready
- 🧪 Tests: 21+ unit tests (T006/T008/T010/T012/T014/T021/T023) + 5 integration test classes (T025–T029) specified
- 📁 Files: specs/006-production-agent/tasks.md created
- 🔁 Next prompts: /sp.implement (start at T001)
- 🧠 Reflection: RED-GREEN pattern applied per tool — each tool task immediately followed by its unit test task; integration tests deferred to Phase 6 to keep Phase 3 focussed

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): n/a (task generation, not code)
- Prompt variant (if applicable): n/a
- Next experiment (smallest change to try): start /sp.implement at T001 and validate schema before moving to tools
