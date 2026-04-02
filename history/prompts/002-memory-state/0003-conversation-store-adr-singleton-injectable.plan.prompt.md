---
id: "0003"
title: "ConversationStore ADR Singleton vs Injectable"
stage: plan
date: 2026-04-02
surface: agent
model: claude-sonnet-4-6
feature: 002-memory-state
branch: 002-memory-state
user: Muhammad Qasim
command: /sp.adr
labels: ["adr","singleton","dependency-injection","conversation-store","phase-2c","phase-4a"]
links:
  spec: specs/002-memory-state/spec.md
  ticket: null
  adr: history/adr/0001-conversation-store-singleton-vs-injectable.md
  pr: null
files:
  - history/adr/0001-conversation-store-singleton-vs-injectable.md
tests:
  - tests/test_core_loop.py (existing — regression guard)
  - tests/test_prototype.py (existing — regression guard)
  - tests/unit/test_conversation_store.py (future — direct instantiation pattern documented)
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

### Part A — Run the ADR first (quick)
/sp.adr conversation-store-singleton-vs-injectable
Document the tradeoff. This is important for Phase 4A PostgreSQL migration.

## RULES
- Work in /home/ps_qasim/projects/crm-digital-fte
- no implementation code yet
- Commit ADR when done, do NOT push

## WHEN DONE
Confirm: ADR file path
```

## Response snapshot

Created ADR-0001 at `history/adr/0001-conversation-store-singleton-vs-injectable.md`.

Decision: Module-level singleton via `get_store()` factory, with `ConversationStore` directly
instantiable for test isolation. Three alternatives rejected: explicit DI parameter (breaks 16
existing tests; deferred to Phase 4A), class-level `__new__` singleton (kills test isolation),
DI container library (overkill). Key consequence: singleton is not async-safe; Phase 4A must
replace with FastAPI `Depends()` — get_store() is the single swap point.

## Outcome

- ✅ Impact: ADR-0001 created; singleton pattern decision captured with Phase 4A migration path explicit
- 🧪 Tests: No new tests (planning phase); direct instantiation pattern documented in ADR
- 📁 Files: 1 ADR created under history/adr/
- 🔁 Next prompts: /sp.tasks for Phase 2C — implement ConversationStore per singleton pattern in ADR-0001
- 🧠 Reflection: "get_store() is the single swap point for Phase 4A" is the load-bearing justification for accepting the singleton's negatives

## Evaluation notes (flywheel)

- Failure modes observed: None — decision was clear-cut given Phase 4A migration requirement
- Graders run and results (PASS/FAIL): Significance test PASS (cross-cutting, 3 alternatives, revisited in Phase 4A)
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): In Phase 4A plan, capture FastAPI Depends() replacement as follow-on ADR referencing ADR-0001
