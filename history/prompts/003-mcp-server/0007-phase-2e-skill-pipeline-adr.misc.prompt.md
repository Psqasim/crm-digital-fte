---
id: "0007"
title: Phase 2E Skill Pipeline ADR
stage: misc
date: 2026-04-03
surface: agent
model: claude-sonnet-4-6
feature: 003-mcp-server
branch: 003-mcp-server
user: Muhammad Qasim
command: /sp.adr
labels: ["adr", "agent-skills", "phase-2e", "async", "skill-pipeline"]
links:
  spec: specs/003-mcp-server/spec-2e-agent-skills.md
  ticket: null
  adr: history/adr/0002-skill-pipeline-synchronous-vs-asynchronous-design.md
  pr: null
files:
  - history/adr/0002-skill-pipeline-synchronous-vs-asynchronous-design.md
tests:
  - null
---

## Prompt

## CONTEXT
Project: CRM Digital FTE Factory — GIAIC Hackathon 5
Location: /home/ps_qasim/projects/crm-digital-fte
Branch: 003-mcp-server
Phase: 2E — Agent Skills

Plan: specs/003-mcp-server/plan-2e-agent-skills.md (10 tasks)
Contract: specs/003-mcp-server/contracts/skills_invoker_contract.py
79/79 tests currently passing — must stay green

## TASK
Do things in order:

### Part A — ADR first (quick)
/sp.adr skill-pipeline-sync-vs-async
Document: sync is correct for Phase 2E prototype, must become async for 
Phase 4E Kafka workers. Include migration path notes.

## RULES
- Work in /home/ps_qasim/projects/crm-digital-fte
- Commit both ADR, do NOT push

## WHEN DONE
Confirm: ADR path + any HIGH RISK flagged.

## Response snapshot

Created ADR-0002 at `history/adr/0002-skill-pipeline-synchronous-vs-asynchronous-design.md`.

**Decision**: Synchronous sequential pipeline for Phase 2E. `SkillsInvoker.run()` and all 5 adapter methods are plain synchronous functions wrapping existing synchronous modules. No `asyncio`, no threads, no event loop.

**Phase 4 migration path**: Create `AsyncSkillsInvoker(SkillsInvoker)` subclass that overrides `run()` and `apply_channel_adaptation()` with `async def`. Keep `SkillsInvoker` as `SyncSkillsInvoker` for CLI and tests. All 79 existing tests stay green unchanged.

**HIGH RISK flagged**: `evaluate_escalation()` makes a blocking OpenAI API call. In Phase 4 async context this blocks the entire event loop. Must be wrapped with `asyncio.to_thread(evaluate_escalation, message)` in `AsyncSkillsInvoker._run_escalation_decision()`. Capture as mandatory pre-flight item in Phase 4 plan.

**Alternatives rejected**: async-first with `asyncio.run()` (breaks existing tests), ThreadPoolExecutor (thread-safety risk on ConversationStore singleton), anyio (irrelevant — aiokafka requires asyncio).

**Significance test**: PASS — impact (cross-cutting: affects every skill call), alternatives (3 considered), scope (affects Phase 4 Kafka worker architecture, not isolated).

## Outcome

- ✅ Impact: ADR-0002 documents sync/async design decision with Phase 4 migration contract
- 🧪 Tests: no new tests — ADR is documentation only
- 📁 Files: history/adr/0002-skill-pipeline-synchronous-vs-asynchronous-design.md
- 🔁 Next prompts: /sp.tasks for Phase 2E
- 🧠 Reflection: HIGH RISK item (blocking OpenAI call) surfaced early — Phase 4 planning can address before it becomes a runtime incident

## Evaluation notes (flywheel)

- Failure modes observed: create-adr.sh required --title flag (not positional arg)
- Graders run and results (PASS/FAIL): significance test — all 3 criteria PASS
- Prompt variant (if applicable): null
- Next experiment: null
