---
id: "0015"
title: Phase 4D FastAPI Orchestration Agent Routes Worker Health
stage: green
date: 2026-04-08
surface: agent
model: claude-sonnet-4-6
feature: 006-production-agent
branch: 007-production-fastapi
user: Muhammad Qasim
command: /sp.implement
labels: ["phase-4d","fastapi","agent-routes","health","worker","background-tasks"]
links:
  spec: specs/006-production-agent/spec.md
  ticket: null
  adr: history/adr/0003-tool-input-schema-design-pydantic-basemodel-vs-typeddict.md
  pr: https://github.com/Psqasim/crm-digital-fte/pull/5
files:
  - production/api/main.py
  - production/api/agent_routes.py
  - production/database/queries.py
  - production/workers/message_processor.py
  - production/tests/test_agent_routes.py
  - production/tests/test_health.py
tests:
  - production/tests/test_agent_routes.py::test_process_single_ticket_resolved
  - production/tests/test_agent_routes.py::test_process_single_ticket_escalated
  - production/tests/test_agent_routes.py::test_process_single_ticket_not_found
  - production/tests/test_agent_routes.py::test_process_pending_queues_tickets
  - production/tests/test_agent_routes.py::test_process_pending_empty
  - production/tests/test_health.py::test_health_healthy
  - production/tests/test_health.py::test_health_degraded
  - production/tests/test_health.py::test_health_response_shape
---

## Prompt

 ## CONTEXT
Project: CRM Digital FTE Factory — GIAIC Hackathon 5
Location: /home/ps_qasim/projects/crm-digital-fte
Phase: 4D — FastAPI Main Service (Agent Orchestration)

Previous phases complete:
- 4B: OpenAI Agents SDK agent (production/agent/customer_success_agent.py)
- 4C: Channel handlers + web form endpoints (production/api/web_form_routes.py)
- DB: 8 tables live on Neon PostgreSQL
Current tests: 142 passing

Read before starting:
- production/api/main.py (current state)
- production/agent/customer_success_agent.py (process_ticket function)
- production/database/queries.py (all 13 functions)
- specs/customer-success-fte-spec.md (§7 performance requirements)

## MANDATORY — USE CONTEXT7 BEFORE ANY CODE
Search:
1. "fastapi background tasks backgroundtasks"
2. "fastapi lifespan startup shutdown asyncpg pool"
3. "openai agents sdk runner run async"

## TASK
Create fresh branch: 007-production-fastapi
From: main

### Step 1: production/api/main.py — complete FastAPI app
Full app with lifespan (not deprecated @app.on_event), register ALL routers, CORS middleware.

### Step 2: production/api/agent_routes.py — agent orchestration
POST /agent/process/{ticket_id} + POST /agent/process-pending with BackgroundTasks

### Step 3: production/workers/message_processor.py
Async loop every 30s, calls /agent/process-pending via httpx, handles connection errors.

### Step 4: GET /health endpoint
Tests DB (SELECT 1), returns healthy/degraded, PKT timestamp, never 500.

### Step 5: Update production/tests/
test_agent_routes.py + test_health.py — 142+ must stay green.

### Step 6: End-to-end smoke test
curl -X POST http://localhost:8000/agent/process/TKT-D5D3DC75

### Step 7: Commit, push, merge via GitHub MCP

## RULES
- Context7 MUST be used before code
- Load .env via python-dotenv at top of main.py
- Run pytest after implementation — 142 must stay green
- Do NOT hardcode any credentials

## Response snapshot

Implemented Phase 4D in full:

**Branch**: 007-production-fastapi (merged → main as PR #5)

**Endpoints registered** (8 total):
- POST /webhooks/gmail, POST /webhooks/whatsapp
- POST /support/submit, GET /support/ticket/{id}, GET /metrics/summary
- POST /agent/process/{ticket_id}, POST /agent/process-pending
- GET /health

**Files created/modified**:
1. `production/api/main.py` — asynccontextmanager lifespan, DB pool init, CORS, all routers
2. `production/api/agent_routes.py` (NEW) — single/batch processing, BackgroundTasks for pending
3. `production/database/queries.py` — get_ticket_by_display_id now returns conversation_id + customer_id; new get_pending_tickets()
4. `production/workers/message_processor.py` — httpx async poll loop every 30s
5. `production/tests/test_agent_routes.py` (NEW) — 5 tests (resolved, escalated, 404, pending, empty)
6. `production/tests/test_health.py` (NEW) — 3 tests (healthy, degraded, shape)

**Test results**: 150 passed, 19 skipped (was 142 before)

**Smoke test**: TKT-D5D3DC75 processed → status updated open → resolved in DB

**PR**: https://github.com/Psqasim/crm-digital-fte/pull/5 — merged (2d9dcbe)

## Outcome

- ✅ Impact: Phase 4D complete — FastAPI fully wired with agent orchestration, health check, and background worker
- 🧪 Tests: 150 passed, 19 skipped (8 new tests added for agent routes + health)
- 📁 Files: 3 new files, 3 modified files
- 🔁 Next prompts: Phase 4E — Kafka consumer integration
- 🧠 Reflection: BackgroundTasks pattern from Context7 confirmed; lifespan asynccontextmanager pattern used correctly (no deprecated @app.on_event)

## Evaluation notes (flywheel)

- Failure modes observed: Port 8000 was in use during smoke test — killed with fuser -k before retry
- Graders run and results (PASS/FAIL): pytest 150/150 PASS; smoke test PASS (ticket resolved)
- Prompt variant (if applicable): null
- Next experiment: Add Kafka consumer in Phase 4E to replace httpx polling worker
