---
id: "004"
title: Generate Phase 2B Task Breakdown
stage: tasks
date: 2026-04-01
surface: agent
model: claude-sonnet-4-6
feature: 001-incubation-exploration
branch: 001-incubation-exploration
user: Muhammad Qasim
command: /sp.tasks
labels: ["tasks","prototype","phase-2b","escalation","core-loop","high-risk"]
links:
  spec: specs/001-incubation-exploration/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/001-incubation-exploration/tasks.md
tests:
  - tests/test_escalation_evaluator.py (stub — to be created in T007)
  - tests/test_core_loop.py (stub — to be created in T009)
  - tests/test_prototype.py (to be created in T011)
---

## Prompt

```text
## CONTEXT
Project: CRM Digital FTE Factory — GIAIC Hackathon 5
Location: /home/ps_qasim/projects/crm-digital-fte
Branch: 001-incubation-exploration
Phase: 2B — Prototype Core Loop

sp.plan is complete. Plan file at specs/001-incubation-exploration/plan.md
9 tasks defined (T1–T9). Highest risk: T6 (escalation evaluator), T8 (core loop).
Data contracts at specs/001-incubation-exploration/contracts/

## TASK
Run /sp.tasks

Generate the full task breakdown for all 9 tasks from plan.md.
Each task must include:
- Exact file to create/modify
- Acceptance criteria (how we know it's done)
- Dependencies (which tasks must come first)
- Test stub needed: yes/no

Flag T6 and T8 as HIGH RISK — generate test stubs for those first.

## RULES
- Work in /home/ps_qasim/projects/crm-digital-fte
- This is task breakdown only — no implementation code yet
- Commit when done, do NOT push

## WHEN DONE
Confirm: tasks file path + all 9 tasks listed with acceptance criteria.
Ready for sp.implement: yes/no
```

## Response snapshot

Generated `specs/001-incubation-exploration/tasks.md` with 12 tasks (T001–T012) organized across 6 phases.

Plan T1–T9 mapped as:
- T001 = T1 (setup), T002 = T2 (data models), T003 = T7 (prompts)
- T004/T005/T006 = T3/T4/T5 (normalization, KB, formatter) → US1
- T007 = escalation test stub [HIGH RISK], T008 = T6 escalation evaluator [HIGH RISK] → US3
- T009 = core loop test stub [HIGH RISK], T010 = T8 core loop [HIGH RISK] → US3
- T011 = T9 CLI + verification → US4
- T012 = quickstart validation (polish)

Test stubs added for T6 (→ T007: `tests/test_escalation_evaluator.py`) and T8 (→ T009: `tests/test_core_loop.py`) — must FAIL before implementation tasks T008/T010 begin.

## Outcome

- ✅ Impact: Full 12-task breakdown ready for sp.implement; HIGH RISK tasks have TDD guard rails; all 9 plan.md tasks covered with exact file paths and acceptance criteria
- 🧪 Tests: T007 and T009 are test stubs (failing) that gate T008 and T010; T011 adds test_prototype.py for 5-ticket end-to-end verification
- 📁 Files: specs/001-incubation-exploration/tasks.md (created)
- 🔁 Next prompts: /sp.implement — start with T001 (setup), then T002+T003 in parallel, then T004+T005+T006 in parallel, then T007+T009 test stubs before T008+T010
- 🧠 Reflection: Mapping plan.md T1–T9 to spec.md user stories (US1/US3/US4) provides clear story-level traceability; test stubs for HIGH RISK tasks enforce TDD discipline on the most error-prone escalation and core loop logic

## Evaluation notes (flywheel)

- Failure modes observed: none — prerequisites check, plan.md, data-model.md, contracts all loaded cleanly
- Graders run and results (PASS/FAIL): n/a (task generation phase — no runnable tests yet)
- Prompt variant (if applicable): null
- Next experiment: validate T007 test stub fails before starting T008 escalation evaluator implementation
