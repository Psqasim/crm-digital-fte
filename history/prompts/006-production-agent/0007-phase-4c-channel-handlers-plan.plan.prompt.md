---
id: "0007"
title: "Phase 4C Channel Handlers Plan"
stage: plan
date: 2026-04-04
surface: agent
model: claude-sonnet-4-6
feature: 006-production-agent
branch: 006-production-agent
user: Muhammad Qasim
command: /sp.plan
labels: ["plan","channel-handlers","gmail","whatsapp","kafka","fastapi","phase-4c","high-risk"]
links:
  spec: specs/006-production-agent/spec-4c-channel-handlers.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/006-production-agent/plan-4c-channel-handlers.md
tests:
  - none
---

## Prompt

## CONTEXT
Project: CRM Digital FTE Factory — GIAIC Hackathon 5
Location: /home/ps_qasim/projects/crm-digital-fte
Branch: 006-production-agent
Phase: 4C-i + 4C-ii — Gmail + WhatsApp Handlers

Spec: specs/006-production-agent/spec-4c-channel-handlers.md

## TASK
Run /sp.plan for Phase 4C-i + 4C-ii.

Plan must cover:

**Shared infrastructure:**
- production/channels/kafka_producer.py — shared async Kafka producer
  (one producer, used by both handlers + web form in 4C-iii)
- Topic: "fte.tickets.incoming" — single unified topic
- Message schema: {ticket_id, customer_email, channel, content,
  metadata, timestamp_pkt}

**Gmail Handler (production/channels/gmail_handler.py):**
- GmailHandler class with: setup_credentials(), watch_inbox(),
  process_pub_sub_push(payload), send_reply(thread_id, message)
- Two-step flow: Pub/Sub delivers historyId → call history.list()
  → get full message
- In-memory dedup set for message_id

**WhatsApp Handler (production/channels/whatsapp_handler.py):**
- WhatsAppHandler class with: validate_signature(request),
  process_webhook(payload), send_reply(to_phone, message)
- Twilio RequestValidator for signature check → HTTP 403 on fail
- MessageSid dedup set

**Required env vars to add to .env.example:**
Gmail: GMAIL_CREDENTIALS_JSON, GMAIL_USER_EMAIL, GOOGLE_CLOUD_PROJECT_ID
Twilio: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER

**Tests:**
- test_gmail_handler.py — mock Gmail API client, test two-step flow,
  test dedup (same message_id twice → processed once)
- test_whatsapp_handler.py — mock Twilio validator + client,
  test signature rejection (403), test MessageSid dedup

Flag HIGH RISK tasks.

## RULES
- Work in /home/ps_qasim/projects/crm-digital-fte
- Planning only — no code yet
- Commit when done, do NOT push

## WHEN DONE
Confirm: plan file path + task count + HIGH RISK tasks.
Ready for sp.tasks: yes/no

## Response snapshot

Created `specs/006-production-agent/plan-4c-channel-handlers.md` with 8 tasks, 40 subtasks.

**4 HIGH RISK tasks flagged:**
- Task 2 (gmail_handler.py): OAuth2 token loading + two-step history.list state management
- Task 3 (whatsapp_handler.py): Twilio URL reconstruction for HMAC signature validation
- Task 4 (api/webhooks.py): X-Forwarded-Proto proxy awareness for Twilio signature
- Task 5 (tools.py): Touching live Phase 4B code — must not break 122 passing tests

**Key architectural decisions:**
- `aiokafka` chosen for native async compatibility (matches asyncpg/openai-agents pattern)
- Kafka singleton via `get_kafka_producer()` lazy init, started in FastAPI lifespan event
- Lazy imports in `send_response` to avoid circular imports
- `thread_id` + `recipient` added as optional fields to `SendResponseInput` (backwards compatible)

## Outcome

- ✅ Impact: Complete implementation plan for both channel handlers; 8 tasks, all HIGH RISK items identified with mitigations
- 🧪 Tests: 20 tests planned (10 per handler); all Gmail API and Twilio calls mocked
- 📁 Files: specs/006-production-agent/plan-4c-channel-handlers.md
- 🔁 Next prompts: /sp.tasks for Phase 4C then /sp.implement
- 🧠 Reflection: Task 4.4 (X-Forwarded-Proto) is often missed — Twilio always signs with https but dev servers may receive http; including it now prevents a hard-to-debug production issue

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): n/a — plan phase
- Prompt variant (if applicable): n/a
- Next experiment (smallest change to try): Run /sp.tasks to decompose into testable implementation tasks
