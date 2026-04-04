---
id: "0004"
title: "Phase 2C Memory State Tasks"
stage: tasks
date: 2026-04-02
surface: agent
model: claude-sonnet-4-6
feature: 002-memory-state
branch: 002-memory-state
user: Muhammad Qasim
command: /sp.tasks
labels: ["tasks","memory","state","conversation-store","phase-2c","tdd"]
links:
  spec: specs/002-memory-state/spec.md
  ticket: null
  adr: history/adr/0001-conversation-store-singleton-vs-injectable.md
  pr: null
files:
  - specs/002-memory-state/tasks.md
tests:
  - tests/unit/test_conversation_store.py (new — 25+ test cases across 8 phases)
  - tests/test_core_loop.py (regression guard)
  - tests/test_escalation_evaluator.py (regression guard)
  - tests/test_prototype.py (regression guard)
---

## Prompt

```text
## CONTEXT
Project: CRM Digital FTE Factory — GIAIC Hackathon 5
Location: /home/ps_qasim/projects/crm-digital-fte
Branch: 002-memory-state
Phase: 2C — Memory & State

Plan: specs/002-memory-state/plan.md (8 task areas)
Contract stub: specs/002-memory-state/contracts/store_interface.py (13 typed methods)
Data model: specs/002-memory-state/data-model.md

## TASK
### Part B — Run /sp.tasks
Break down all 8 task areas into individual implementable tasks.
Each task must have:
- Exact file to create or modify
- Acceptance criteria
- Dependencies
- Test needed: yes/no

Flag any HIGH RISK tasks.

## RULES
- Work in /home/ps_qasim/projects/crm-digital-fte
- Tasks breakdown only after ADR — no implementation code yet
- Commit both ADR and tasks when done, do NOT push

## WHEN DONE
Confirm: ADR file path + tasks file path + total task count.
Ready for sp.implement: yes/no
```

## Response snapshot

Generated `specs/002-memory-state/tasks.md` with 41 tasks across 8 phases:

- Phase 1 (Setup): T001–T002 — create skeleton files
- Phase 2 (Foundational): T003–T006 — models.py extensions + ConversationStore constants + get_store()
- Phase 3 (US1 P1 Multi-Turn): T007–T016 — customer/conversation/message/context + 2 HIGH RISK prototype.py integrations
- Phase 4 (US2 P2 Cross-Channel): T017–T022 — resolve_identity + link_phone_to_email + transient merge (1 HIGH RISK)
- Phase 5 (US3 P3 Sentiment): T023–T027 — compute_sentiment_trend + URGENCY_SCORE_MAP
- Phase 6 (US4 P3 Status): T028–T033 — Ticket.transition + transition_ticket + escalation path (1 HIGH RISK)
- Phase 7 (US5 P4 Topics): T034–T038 — add_topic + has_prior_topic + prior_note injection
- Phase 8 (Polish): T039–T041 — FR-011 isolation test + regression gate

HIGH RISK guard defined: run 16 Phase 2B tests before committing T015, T016, T021, T033.
Prototype.py change sequence documented: T015→T016→T022→T027→T033→T038 (strictly sequential).
US3+US4 (both P3) can be parallelised — different methods in conversation_store.py.

## Outcome

- ✅ Impact: 41-task breakdown ready for /sp.implement with per-story checkpoints
- 🧪 Tests: TDD approach — test tasks precede every implementation phase; 25+ test functions across 8 test groups
- 📁 Files: 1 tasks file created
- 🔁 Next prompts: /sp.implement for Phase 2C
- 🧠 Reflection: The prototype.py change sequence (T015→T016→T022→T027→T033→T038) is the highest-risk chain in this feature — all 6 touches same function; must be done strictly in order with regression runs between each

## Evaluation notes (flywheel)

- Failure modes observed: None — task boundaries are clean; each phase has an independent checkpoint
- Graders run and results (PASS/FAIL): Format check PASS (all 41 tasks have ID + file path); story coverage PASS (all 5 user stories covered)
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): Consider splitting T015+T016 into a feature-flag approach (add `USE_STORE = os.getenv("USE_STORE", "false")`) to allow gradual rollout without breaking existing tests during development
