---
id: "0001"
title: Phase 4A PostgreSQL Schema and Queries
stage: green
date: 2026-04-04
surface: agent
model: claude-sonnet-4-6
feature: 005-production-db
branch: 005-production-db
user: Muhammad Qasim
command: Phase 4A implementation prompt (inline)
labels: ["database","postgresql","pgvector","asyncpg","migrations","phase-4a"]
links:
  spec: specs/customer-success-fte-spec.md
  ticket: null
  adr: null
  pr: https://github.com/Psqasim/crm-digital-fte/pull/3
files:
  - production/database/schema.sql
  - production/database/migrations/001_initial_schema.sql
  - production/database/migrations/002_seed_channel_configs.sql
  - production/database/queries.py
  - production/database/seed_knowledge_base.py
  - production/requirements.txt
  - .env.example
  - production/tests/test_database.py
tests:
  - production/tests/test_database.py (11 tests, 11 skipped — no TEST_DATABASE_URL)
  - tests/ (101/101 passing — no regressions)
---

## Prompt

Phase 4A — PostgreSQL Schema (Neon + pgvector).

Context7 MCP lookups required before writing any schema:
1. asyncpg connection pool + Neon DSN format
2. pgvector vector column syntax + ivfflat cosine index
3. OpenAI embeddings API syntax

Then implement:
- production/database/schema.sql — 8 tables with extensions and 13 indexes
- production/database/migrations/001_initial_schema.sql + 002_seed_channel_configs.sql
- production/database/queries.py — 13 async functions, injectable pool (ADR-0001)
- production/database/seed_knowledge_base.py — chunk product-docs.md, embed, upsert
- .env.example — DATABASE_URL + TEST_DATABASE_URL (Neon format)
- production/tests/test_database.py — pytest-asyncio, skip if no TEST_DATABASE_URL
- Commit feat: Phase 4A, push branch 005-production-db, PR → merge to main

## Response snapshot

Context7 verified:
- asyncpg: `asyncpg.create_pool(dsn=DATABASE_URL)` with DSN string format
- pgvector: `vector(1536)` column type; `USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)`

Implemented all 8 tasks:
1. schema.sql — 8 tables (customers, customer_identifiers, conversations, messages, tickets, knowledge_base, channel_configs, agent_metrics); 2 extensions; 13 indexes
2. migrations/001 (schema copy) + migrations/002 (channel seed — email 2500/formal, whatsapp 1600/conversational, web_form 5000/semi_formal from brand-voice.md)
3. queries.py — 13 async functions: get_db_pool, get_or_create_customer, resolve_phone_to_customer, link_phone_to_customer, create_conversation, add_message, get_customer_history, get_sentiment_trend, create_ticket, update_ticket_status, search_knowledge_base, upsert_knowledge_base, record_metric — all injectable pool, all try/except logging
4. seed_knowledge_base.py — heading-split + 500-word window chunking, batch OpenAI embeddings, asyncpg upsert
5. production/requirements.txt — asyncpg>=0.29.0 added
6. .env.example — DATABASE_URL + TEST_DATABASE_URL Neon format
7. test_database.py — 11 pytest-asyncio tests (get_or_create idempotent, phone link/resolve, conversation+message+history, ticket status transitions, metrics); skip if no TEST_DATABASE_URL
8. Committed, pushed, PR #3 created and merged to main (merge commit: 72313f1)

Test results: 11 skipped (no TEST_DATABASE_URL), 101/101 existing tests passing.

## Outcome

- ✅ Impact: Phase 4A complete — production PostgreSQL layer fully implemented and merged to main
- 🧪 Tests: 11 DB tests skipped cleanly (CI-safe); 101/101 existing suite passing
- 📁 Files: 8 files created/modified across production/database/ and root
- 🔁 Next prompts: Phase 4B — OpenAI Agents SDK customer_success_agent.py
- 🧠 Reflection: Context7 verification before schema write prevented any pgvector syntax guesswork. Injectable pool pattern enforced throughout for testability (ADR-0001). Seed script uses heading-boundary chunking with 50-word overlap to handle long sections.

## Evaluation notes (flywheel)

- Failure modes observed: asyncpg not in venv initially — installed via uv; Write tool rejected stale-read on placeholder files — re-read before writing resolved it
- Graders run and results (PASS/FAIL): pytest tests/ — PASS (101/101); pytest production/tests/ — PASS (11/11 skipped cleanly)
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): Run test_database.py with live Neon TEST_DATABASE_URL to validate all 11 tests end-to-end before Phase 4B
