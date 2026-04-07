---
id: "0006"
title: "Phase 4C Channel Handlers Spec"
stage: spec
date: 2026-04-04
surface: agent
model: claude-sonnet-4-6
feature: 006-production-agent
branch: 006-production-agent
user: Muhammad Qasim
command: /sp.specify
labels: ["spec","channel-handlers","gmail","whatsapp","twilio","kafka","phase-4c"]
links:
  spec: specs/006-production-agent/spec-4c-channel-handlers.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/006-production-agent/spec-4c-channel-handlers.md
  - specs/006-production-agent/checklists/requirements-4c.md
tests:
  - none
---

## Prompt

## CONTEXT
Project: CRM Digital FTE Factory — GIAIC Hackathon 5
Location: /home/ps_qasim/projects/crm-digital-fte
Branch: 006-production-agent (continue — 4C is part of same production build)
Phase: 4C-i + 4C-ii — Gmail Handler + WhatsApp/Twilio Handler

Phase 4B complete: 7 @function_tool agent with 122 tests passing.
send_response tool is currently a STUB — these handlers will make it real.

Read before specifying:
- ./The CRM Digital FTE Factory Final Hackathon 5.md (Channel Requirements table)
- specs/customer-success-fte-spec.md (§2 Supported Channels)
- production/agent/tools.py (send_response stub — this gets replaced)
- .claude/skills/email-automation/ (read this skill fully)
- context/brand-voice.md (channel tone rules)

## MANDATORY — USE CONTEXT7 BEFORE SPECIFYING
Search these now:
1. "gmail api python watch pub/sub webhook" — Gmail push notification setup
2. "twilio whatsapp webhook signature validation python" — Twilio security
3. "twilio python send whatsapp message" — reply API

## TASK
Run /sp.specify for Phase 4C-i + 4C-ii (combined).

**Gmail Handler (production/channels/gmail_handler.py):**
- Receive Gmail Pub/Sub push notification (POST webhook)
- Decode base64 message data from Pub/Sub payload
- Extract: sender email, subject, body, thread_id
- Normalize into TicketMessage format (channel="email")
- Push normalized message to Kafka topic: "tickets.email"
- Send reply via Gmail API using thread_id (keep email thread intact)
- Handle: missing credentials gracefully, base64 decode errors,
  duplicate message detection (Pub/Sub delivers at-least-once)

**WhatsApp Handler (production/channels/whatsapp_handler.py):**
- Receive Twilio webhook POST
- Validate Twilio signature (X-Twilio-Signature header) — security required
- Extract: From (phone), Body (message), MessageSid
- Normalize into TicketMessage (channel="whatsapp")
- Push to Kafka topic: "tickets.whatsapp"
- Reply via Twilio REST API (twilio-python client)
- Handle: duplicate MessageSid, empty body, media messages (ignore attachments)

**Both handlers share:**
- Deduplication: MessageSid / Gmail message_id stored in-memory set
  (Redis in production, but in-memory is fine for hackathon)
- Normalization produces same TicketMessage schema as prototype
- Errors logged to stderr, never crash the webhook endpoint

## RULES
- Work in /home/ps_qasim/projects/crm-digital-fte
- Specify only — no code yet
- Commit when done, do NOT push

## WHEN DONE
Confirm: spec file path + both handlers covered. Ready for sp.plan: yes/no

## Response snapshot

Created `specs/006-production-agent/spec-4c-channel-handlers.md` covering both handlers:

**Gmail Handler (4C-i):** FR-GH-001 through FR-GH-009 — Pub/Sub push webhook, two-step
history.list flow (historyId → actual messages), TicketMessage normalisation with
`channel="email"` and `metadata["thread_id"]`, Kafka publish to `tickets.email`, Gmail API
threaded reply, in-memory message_id deduplication, graceful credential error handling.

**WhatsApp Handler (4C-ii):** FR-WH-001 through FR-WH-009 — Twilio webhook, RequestValidator
signature check (HTTP 403 on failure), TicketMessage normalisation with `channel="whatsapp"`,
Kafka publish to `tickets.whatsapp`, Twilio messages.create reply, MessageSid deduplication,
media-only message placeholder, never-crash guarantee.

**Shared:** FR-SH-001 through FR-SH-005 — in-memory dedup, stderr logging, fault isolation,
TicketMessage schema parity, env-var startup behaviour.

1 clarification needed (Assumptions §8): Kafka topic routing — channel-specific topics
(`tickets.email` / `tickets.whatsapp`) vs. single unified `fte.tickets.incoming`.

## Outcome

- ✅ Impact: Spec complete for both channel handlers; send_response stub has a clear contract to implement against
- 🧪 Tests: No new tests (spec phase — tests defined in User Scenarios for planning phase)
- 📁 Files: specs/006-production-agent/spec-4c-channel-handlers.md, specs/006-production-agent/checklists/requirements-4c.md
- 🔁 Next prompts: Resolve Kafka topic clarification Q1, then /sp.plan for Phase 4C
- 🧠 Reflection: Context7 confirmed critical Gmail detail — Pub/Sub delivers historyId not full message; history.list call is mandatory. Twilio RequestValidator pattern confirmed for signature security.

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): n/a — spec phase
- Prompt variant (if applicable): n/a
- Next experiment (smallest change to try): Resolve Kafka topic routing question, then proceed to /sp.plan
