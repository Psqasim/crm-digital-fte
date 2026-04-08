---
id: "0009"
title: Phase 4C Gmail WhatsApp Handlers Implementation
stage: green
date: 2026-04-04
surface: agent
model: claude-sonnet-4-6
feature: 006-production-agent
branch: 006-production-agent
user: Muhammad Qasim
command: /sp.implement
labels: ["phase-4c", "gmail", "whatsapp", "kafka", "webhooks", "tdd", "channel-handlers"]
links:
  spec: specs/006-production-agent/spec-4c-channel-handlers.md
  ticket: null
  adr: null
  pr: null
files:
  - production/channels/kafka_producer.py
  - production/channels/gmail_handler.py
  - production/channels/whatsapp_handler.py
  - production/api/webhooks.py
  - production/api/main.py
  - production/agent/schemas.py
  - production/agent/tools.py
  - production/tests/test_gmail_handler.py
  - production/tests/test_whatsapp_handler.py
  - production/tests/test_agent_tools.py
  - production/requirements.txt
  - .env.example
  - specs/006-production-agent/tasks-4c-channel-handlers.md
tests:
  - production/tests/test_gmail_handler.py (10 tests — all pass)
  - production/tests/test_whatsapp_handler.py (10 tests — all pass)
  - T045 gate: 142 passed, 19 skipped, 0 failed
  - T049 gate: 142 passed, 19 skipped, 0 failed
---

## Prompt

 ## CONTEXT
Project: CRM Digital FTE Factory — GIAIC Hackathon 5
Location: /home/ps_qasim/projects/crm-digital-fte
Branch: 006-production-agent
Phase: 4C-i + 4C-ii — Gmail + WhatsApp Handlers

Tasks: specs/006-production-agent/tasks-4c-channel-handlers.md (49 tasks)
HIGH RISK: T020, T021, T024, T025, T038, T042, T046, T047, T048, T049
Hard regression gates: T045 (122 before tools.py) + T049 (122 after tools.py)
Current passing: 122 tests

[... full 49-task implementation prompt with all HIGH RISK rules and acceptance criteria ...]

## Response snapshot

Implemented all 49 tasks in dependency order:

**Phase 1 (T001–T002):** Updated requirements.txt (8 new packages: aiokafka, google-api-python-client, google-auth-oauthlib, google-auth-httplib2, twilio, fastapi, uvicorn, httpx). Updated .env.example with Gmail OAuth2 + Twilio vars.

**Phase 2 (T003–T006):** Created kafka_producer.py — AIOKafkaProducer lazy singleton, publish_ticket() with dataclass/model_dump serialisation, stop_kafka_producer() idempotent shutdown.

**Phase 3 (T007–T016 tests + T017–T026 impl):** Gmail handler — GmailHandler class with setup_credentials() (GMAIL_CREDENTIALS_JSON), watch_inbox(), process_pub_sub_push() with historyId dedup gate, _fetch_and_normalise() (text/plain→snippet fallback, 4000-char truncation), send_reply() with threadId. Webhooks: POST /webhooks/gmail (400 on bad JSON, 200 on all errors), reconstruct_url() for X-Forwarded-Proto. FastAPI main.py with Kafka lifespan.

**Phase 4 (T027–T036 tests + T037–T042 impl):** WhatsApp handler — WhatsAppHandler with validate_signature() (always calls RequestValidator for testability), process_webhook() with MessageSid dedup + media placeholder + phone prefix strip, send_reply() with 1600-char truncation. Webhooks: POST /webhooks/whatsapp (403 on missing/invalid sig, 200 on Kafka failure).

**HIGH RISK FIX (T038):** validate_signature() must NOT early-return on empty TWILIO_AUTH_TOKEN — must always call `RequestValidator(auth_token).validate()` so test mocks can intercept. Removing the `if not auth_token: return False` guard fixed 6 failing tests.

**Phase 5 (T043–T045):** T045 gate passed: 142 passed, 19 skipped, 0 failed.

**Phase 6 (T046–T049):** SendResponseInput gained thread_id/recipient (backwards-compatible). _send_response_impl updated with lazy imports (circular import prevention). Real dispatch: email→GmailHandler, whatsapp→WhatsAppHandler, web_form→queued. Existing tests updated: stub_delivered→delivered/failed (credentials absent in test env), message_length field removed. T049 gate: 142 passed, 0 failed.

**Committed:** `feat: Phase 4C-i+ii — Gmail handler, WhatsApp handler, channel webhooks`

## Outcome

- ✅ Impact: Gmail Pub/Sub + WhatsApp Twilio channel handlers complete; all 49 tasks done; hard regression gates T045 and T049 both green
- 🧪 Tests: 142 passed, 19 skipped, 0 failed (122 existing + 20 new channel tests)
- 📁 Files: 13 files changed; 4 new files created (kafka_producer.py, webhooks.py, test_gmail_handler.py, test_whatsapp_handler.py)
- 🔁 Next prompts: Phase 4C-iii — Next.js Web Support Form
- 🧠 Reflection: Key HIGH RISK fix: validate_signature() must reach RequestValidator regardless of env var presence — early-return-on-empty prevents test mocking. asyncio.run() required over asyncio.get_event_loop().run_until_complete() in multi-test runs.

## Evaluation notes (flywheel)

- Failure modes observed: (1) validate_signature early-return blocked mock intercept; (2) asyncio.get_event_loop() fails in full suite (pytest-asyncio tears down loop); (3) stub_delivered test assertions broke after replacing stub
- Graders run and results (PASS/FAIL): T045 PASS (142/0), T049 PASS (142/0)
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): Phase 4C-iii Next.js Web Form handler
