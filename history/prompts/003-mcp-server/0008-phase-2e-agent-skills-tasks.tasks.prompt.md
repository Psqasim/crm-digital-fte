---
id: "0008"
title: Phase 2E Agent Skills Tasks
stage: tasks
date: 2026-04-03
surface: agent
model: claude-sonnet-4-6
feature: 003-mcp-server
branch: 003-mcp-server
user: Muhammad Qasim
command: /sp.tasks
labels: ["tasks", "agent-skills", "phase-2e", "skills-invoker", "wiring"]
links:
  spec: specs/003-mcp-server/spec-2e-agent-skills.md
  ticket: null
  adr: history/adr/0002-skill-pipeline-synchronous-vs-asynchronous-design.md
  pr: null
files:
  - specs/003-mcp-server/tasks-2e-agent-skills.md
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

### Part B — Run /sp.tasks
Break down all 10 tasks into implementable units.
Each task must have:
- Exact file to create/modify
- Acceptance criteria
- Dependencies
- Test needed: yes/no
- Flag HIGH RISK if any

Note: T09 (wiring process_ticket through SkillsInvoker) is likely
highest risk — flag it and require pytest run after it.

## RULES
- Work in /home/ps_qasim/projects/crm-digital-fte
- Tasks only — no implementation yet
- Commit tasks, do NOT push

## WHEN DONE
Confirm: tasks file path + total task count + any HIGH RISK flagged.
Ready for sp.implement: yes/no

## Response snapshot

Created `specs/003-mcp-server/tasks-2e-agent-skills.md` with 13 tasks across 11 phases.

**Task breakdown:**
- T001: Verify 5 target function imports
- T002: Create `skills_manifest.py` (SkillManifest dataclass + 5 constants)
- T003: Create `skills_invoker.py` skeleton (result dataclasses + stubs)
- T004: `_run_customer_identification()` (wraps resolve_identity)
- T005: `_run_sentiment_analysis()` (wraps compute_sentiment_trend)
- T006: `_run_knowledge_retrieval()` (wraps KnowledgeBase.search)
- T007: `_run_escalation_decision()` (wraps evaluate_escalation + sentiment supplement)
- T008: `apply_channel_adaptation()` (wraps format_response)
- T009a [P]: `skills_registry.py` (SkillsRegistry class)
- T009b [P]: `SkillsInvoker.run()` pipeline assembly
- T009c ⚠️ HIGH RISK: `prototype.py` wiring (mandatory pytest after)
- T010: `tests/test_skills.py` (22 test cases)
- T011: `CLAUDE.md` update

**HIGH RISK flagged: 1** — T009c modifies `process_ticket` which backs all 79 tests. Mandatory pytest run before commit. Safety protocol: one change at a time, revert on failure.

## Outcome

- ✅ Impact: 13 implementable tasks with exact file paths, acceptance criteria, and dependency order
- 🧪 Tests: T010 adds 22 new test cases; T009c requires full 79-test suite run
- 📁 Files: specs/003-mcp-server/tasks-2e-agent-skills.md
- 🔁 Next prompts: /sp.implement for Phase 2E
- 🧠 Reflection: T009c isolation strategy (one change at a time, revert on failure) is key to keeping tests green

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): dependency graph validated manually — no circular deps
- Prompt variant (if applicable): null
- Next experiment: null
