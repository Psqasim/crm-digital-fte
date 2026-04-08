---
id: "0017"
title: Phase 4D Bug Fixes pgvector UUID MaxTurnsExceeded
stage: green
date: 2026-04-08
surface: agent
model: claude-sonnet-4-6
feature: 006-production-agent
branch: main
user: Muhammad Qasim
command: manual fix request
labels: ["bugfix","pgvector","uuid","max-turns","knowledge-base"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - production/database/queries.py
  - production/agent/tools.py
  - production/agent/customer_success_agent.py
  - production/tests/test_agent_tools.py
tests:
  - production/tests/test_agent_tools.py::test_search_knowledge_base_db_error
  - smoke: POST /agent/process/TKT-440AB752 → resolved, no MaxTurnsExceeded
---

## Prompt

Three bugs blocking agent from processing tickets, identified from logs:

Bug 1: search_knowledge_base — pgvector expects string '[x,y,...]' not Python list
Bug 2: get_customer_history — asyncpg UUID objects not JSON serializable
Bug 3: MaxTurnsExceeded — agent loops retrying failing KB search tool

## Response snapshot

Bug 1 fix — queries.py search_knowledge_base():
  - Added COUNT check: return [] immediately if KB is empty
  - Cast embedding: "[" + ",".join(str(x) for x in embedding) + "]"

Bug 2 fix — queries.py:
  - Added _serialize_row() helper: converts UUID (hasattr hex) and datetime (hasattr isoformat) to str
  - Applied to get_customer_history() messages list

Bug 3 fix — tools.py + customer_success_agent.py:
  - search_knowledge_base returns graceful JSON with "note" key (no "error") on empty/fail
  - max_turns: 10 → 15

Test fix: test_agent_tools.py::test_search_knowledge_base_db_error updated for new response shape

Results: 150 passed, 19 skipped
Smoke: TKT-440AB752 → status: resolved, no errors in logs
Commit: f604234 → main

## Outcome

- ✅ Impact: Agent completes full processing cycle without errors
- 🧪 Tests: 150 passed, 19 skipped (1 test updated for new shape)
- 📁 Files: 4 files changed
- 🔁 Next prompts: Phase 4E — Kafka consumer
- 🧠 Reflection: asyncpg returns native Python types (UUID, datetime) for PostgreSQL types — always serialize at the DB layer, not the API layer

## Evaluation notes (flywheel)

- Failure modes observed: pgvector rejects list type; UUID fails json.dumps; agent retry-loops on error JSON
- Graders run and results (PASS/FAIL): pytest 150/150 PASS; smoke PASS
- Prompt variant (if applicable): null
- Next experiment: Seed knowledge_base table with NexaFlow docs to enable vector search
