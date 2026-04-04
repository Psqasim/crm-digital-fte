---
id: "0003"
title: Phase 4B Production Agent Plan
stage: plan
date: 2026-04-04
surface: agent
model: claude-sonnet-4-6
feature: 006-production-agent
branch: 006-production-agent
user: Muhammad Qasim
command: /sp.plan
labels: ["plan","openai-agents-sdk","production-agent","async-tools","phase-4b"]
links:
  spec: specs/006-production-agent/spec.md
  ticket: null
  adr: history/adr/0003-tool-input-schema-design-pydantic-basemodel-vs-typeddict.md
  pr: null
files:
  - specs/006-production-agent/plan.md
  - specs/006-production-agent/research.md
  - specs/006-production-agent/data-model.md
  - specs/006-production-agent/contracts/tools.md
  - specs/006-production-agent/quickstart.md
  - history/prompts/006-production-agent/0003-phase-4b-production-agent-plan.plan.prompt.md
tests:
  - null
---

## Prompt

## CONTEXT
Project: CRM Digital FTE Factory — GIAIC Hackathon 5
Location: /home/ps_qasim/projects/crm-digital-fte
Branch: 006-production-agent
Phase: 4B — OpenAI Agents SDK Agent

Spec: specs/006-production-agent/spec.md (14/14 checklist pass)
7 tools confirmed. Context7 verified: @function_tool, Runner.run(), 
Pydantic BaseModel inputs, Annotated[T, Field()] constraints.
DB queries ready in production/database/queries.py (13 async functions)
Prototype prompts: src/agent/prompts.py (port to production)

## TASK
Run /sp.plan.

Plan must cover these files:
- production/agent/prompts.py — channel-aware system prompt with datetime injection
- production/agent/tools.py — all 7 @function_tool definitions with Pydantic inputs
- production/agent/formatters.py — port from src/agent/channel_formatter.py
- production/agent/customer_success_agent.py — Agent definition + Runner
- production/tests/test_agent_tools.py — unit tests for each tool
- production/tests/test_agent_integration.py — full agent run tests

Flag highest risk tasks — tools.py wiring to queries.py is likely HIGH RISK
since it bridges async DB calls inside @function_tool decorators.

## Response snapshot

Generated 7 implementation tasks (T-001 through T-007) with full acceptance criteria.

Phase 0 (research.md): 5 unknowns resolved — async @function_tool with asyncpg (R-001), OpenAI embedding singleton (R-002), tool-call ordering via data dependency (R-003), RunResult.final_output extraction (R-004), retry exception types (R-005).

Phase 1 (data-model.md, contracts/tools.md, quickstart.md): All entities, Pydantic input models, 7 tool I/O contracts, local run instructions.

Constitution check: 10 gates — all PASS. No violations.

HIGH RISK: T-004 (tools.py — async asyncpg + embedding inside @function_tool), T-005 (customer_success_agent.py — LLM ordering + retry + RunResult parsing).
MEDIUM RISK: T-006, T-007 (async test mocking).
LOW RISK: T-001, T-002, T-003.

Recommended order: T-001 → T-002 → T-003 → T-006 (scaffolding) → T-004 → T-005 → T-007.

## Outcome

- ✅ Impact: Complete Phase 4B implementation plan — 7 tasks, 5 research resolutions, 4 Phase 1 artifacts
- 🧪 Tests: No tests run (planning phase)
- 📁 Files: plan.md, research.md, data-model.md, contracts/tools.md, quickstart.md
- 🔁 Next prompts: /sp.tasks for Phase 4B
- 🧠 Reflection: Data dependency (ticket_id required by send_response) is a critical structural enforcement for tool ordering — this is more reliable than system prompt instructions alone

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): constitution check — 10/10 PASS; no complexity violations
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): Verify @function_tool async + asyncpg works in a 10-line smoke test before committing to T-004 full implementation
