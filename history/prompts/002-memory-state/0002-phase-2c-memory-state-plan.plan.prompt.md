---
id: "0002"
title: "Phase 2C Memory & State Plan"
stage: plan
date: 2026-04-02
surface: agent
model: claude-sonnet-4-6
feature: 002-memory-state
branch: 002-memory-state
user: Muhammad Qasim
command: /sp.plan
labels: ["plan","memory","state","conversation-store","phase-2c"]
links:
  spec: specs/002-memory-state/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/002-memory-state/plan.md
  - specs/002-memory-state/research.md
  - specs/002-memory-state/data-model.md
  - specs/002-memory-state/quickstart.md
  - specs/002-memory-state/contracts/store_interface.py
tests:
  - tests/test_core_loop.py (existing — must pass)
  - tests/test_escalation_evaluator.py (existing — must pass)
  - tests/test_prototype.py (existing — must pass)
  - tests/unit/test_conversation_store.py (new — to be created in sp.tasks)
---

## Prompt

```text
 ## CONTEXT
Project: CRM Digital FTE Factory — GIAIC Hackathon 5
Location: /home/ps_qasim/projects/crm-digital-fte
Branch: 002-memory-state
Phase: 2C — Memory & State

Spec: specs/002-memory-state/spec.md
6 key entities: Customer Profile, Conversation, Message, Ticket, 
Sentiment Trend, Channel Identity Map.
All state in-memory (dict/list) — no database yet.

## TASK
Run /sp.plan for Phase 2C.

Plan must cover:
- A ConversationStore class (in-memory) that holds all state
- Customer identity resolution (phone → email lookup)
- Conversation history per customer (list of messages with channel metadata)
- Sentiment trend calculation (rolling average across last N messages)
- Resolution status transitions (open → pending → escalated/resolved)
- Topic tracking per customer
- Updating process_ticket in prototype.py to use the store before and after processing

## RULES
- Work in /home/ps_qasim/projects/crm-digital-fte
- Planning only — no code yet
- Commit when done, do NOT push

## WHEN DONE
Confirm: plan file path + number of tasks. Ready for sp.tasks: yes/no
```

## Response snapshot

Generated full Phase 0 + Phase 1 planning artifacts for Phase 2C (Memory & State):

- **research.md** — 8 resolved design decisions covering identity key strategy, in-memory store structure, sentiment score proxy mapping, ticket status transition rules, message cap (20), phone-to-email resolution algorithm, topic label source, and process_ticket integration points.
- **data-model.md** — 6 entities fully defined: CustomerProfile, Conversation, Message, Ticket, SentimentTrend (derived), ChannelIdentityMap. Includes field types, validation rules, status transition table, and sentiment score derivation from urgency proxy.
- **contracts/store_interface.py** — Typed Python stub defining the full ConversationStore public API: 13 methods with preconditions, postconditions, and algorithm descriptions.
- **quickstart.md** — Integration pseudocode showing exactly how `process_ticket` changes, the two store interaction points, the new file layout, sentinel constants, and test patterns.
- **plan.md** — Filled with Technical Context, Constitution Check (all PASS), Project Structure, Phase 0 research summary, Phase 1 artifact table, 8-area task summary, and 3 risk items.

Constitution gate: all 8 checks PASS. No new external dependencies. All 16 Phase 2B tests will be preserved.

## Outcome

- ✅ Impact: Complete planning artifacts for Phase 2C ready for /sp.tasks
- 🧪 Tests: No tests written yet (planning phase); 16 existing tests identified as regression guard
- 📁 Files: 5 new files created under specs/002-memory-state/
- 🔁 Next prompts: /sp.tasks for Phase 2C — generates 8-task breakdown targeting conversation_store.py, models.py, prototype.py, and unit tests
- 🧠 Reflection: Sentinel constant URGENCY_SCORE_MAP is the key design choice — it decouples sentiment scoring from the escalation evaluator without requiring a new LLM call per message

## Evaluation notes (flywheel)

- Failure modes observed: None — spec was fully specified with no NEEDS CLARIFICATION items
- Graders run and results (PASS/FAIL): Constitution check — all 8 gates PASS
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): In /sp.tasks, consider whether sentiment window N should be a constructor parameter on ConversationStore (vs. a module constant) to enable test isolation
