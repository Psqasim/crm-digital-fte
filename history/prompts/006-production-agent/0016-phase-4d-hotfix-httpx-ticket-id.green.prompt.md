---
id: "0016"
title: Phase 4D Hotfix httpx Dep and Ticket ID Context
stage: green
date: 2026-04-08
surface: agent
model: claude-sonnet-4-6
feature: 006-production-agent
branch: main
user: Muhammad Qasim
command: manual fix request
labels: ["hotfix","httpx","agent-context","ticket-id"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - requirements.txt
  - production/api/agent_routes.py
tests:
  - smoke: POST /agent/process/TKT-D5D3DC75 → ticket_id not null
---

## Prompt

Two small fixes after Phase 4D testing:

Fix 1: Add httpx to root requirements.txt (worker import fix)
Fix 2: agent_routes.py — ticket_id=null because agent calls create_ticket with display ID as UUID.
Fix: enrich input message with [EXISTING TICKET] header + real UUIDs so agent skips create_ticket.
Commit directly to main.

## Response snapshot

- requirements.txt: added httpx>=0.27.0
- agent_routes._run_agent_on_ticket: enriched message now includes EXISTING TICKET marker + conversation_id/customer_id UUIDs
- Fallback: agent_resp.ticket_id set from DB if agent doesn't set it
- Worker: starts cleanly (connection error = expected, server not running)
- Smoke test: ticket_id="TKT-D5D3DC75" (not null), no create_ticket UUID errors
- Commit: 32d6957 → main

## Outcome

- ✅ Impact: ticket_id always populated in agent response for existing tickets
- 🧪 Tests: 150 passing (no new tests — behaviour fix only)
- 📁 Files: 2 files changed
- 🔁 Next prompts: Phase 4E — Kafka consumer
- 🧠 Reflection: Agent tool docstring "MUST call create_ticket first" causes the agent to always try it. Fix: explicit system-level message prefix overrides the default tool ordering for existing tickets.

## Evaluation notes (flywheel)

- Failure modes observed: create_ticket tool called with display ID (TKT-XXXXXXXX) as UUID param — asyncpg rejected it
- Graders run and results (PASS/FAIL): smoke PASS — ticket_id not null; worker PASS — starts cleanly
- Prompt variant (if applicable): null
- Next experiment: Long-term fix is a separate tool or agent instruction for "process existing ticket" flow
