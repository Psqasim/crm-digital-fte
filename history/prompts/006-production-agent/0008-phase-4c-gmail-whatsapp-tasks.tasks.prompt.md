---
id: "0008"
title: "Phase 4C Gmail WhatsApp Tasks"
stage: tasks
date: 2026-04-04
surface: agent
model: claude-sonnet-4-6
feature: 006-production-agent
branch: 006-production-agent
user: Muhammad Qasim
command: /sp.tasks
labels: ["tasks","phase-4c","gmail","whatsapp","channel-handlers","high-risk"]
links:
  spec: specs/006-production-agent/spec-4c-channel-handlers.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/006-production-agent/tasks-4c-channel-handlers.md
tests:
  - production/tests/test_gmail_handler.py (10 tests, T007–T016)
  - production/tests/test_whatsapp_handler.py (10 tests, T027–T036)
---

## Prompt

 ## CONTEXT
Project: CRM Digital FTE Factory — GIAIC Hackathon 5
Location: /home/ps_qasim/projects/crm-digital-fte
Branch: 006-production-agent
Phase: 4C-i + 4C-ii — Gmail + WhatsApp Handlers

Plan: specs/006-production-agent/plan-4c-channel-handlers.md
8 tasks / 40 subtasks
HIGH RISK (4):
- Task 2: gmail_handler.py — OAuth2 + historyId state (silent drop risk)
- Task 3: whatsapp_handler.py — Twilio HMAC-SHA1 exact URL match
- Task 4: api/webhooks.py — X-Forwarded-Proto http vs https
- Task 5: tools.py — touching live Phase 4B code (122 test gate)
Current passing: 122 tests

## TASK
Run /sp.tasks for Phase 4C-i + 4C-ii.

Break all 8 tasks / 40 subtasks into individual implementable units.
Each must have:
- Exact file to create/modify
- Acceptance criteria
- Dependencies
- Test needed: yes/no
- HIGH RISK flag

Special attention for HIGH RISK tasks:

**Task 2 subtasks (gmail_handler.py):**
- Separate subtask for credential loading (service account JSON vs OAuth2 flow)
- Separate subtask for historyId state management
  (store last processed historyId, never re-process same history)
- Separate subtask for two-step flow: notification → history.list → messages.get
- Acceptance: process same historyId twice → second call is no-op

**Task 3 subtasks (whatsapp_handler.py):**
- Separate subtask for Twilio RequestValidator setup
- Separate subtask for URL reconstruction
- Acceptance: valid signature → 200, invalid → 403, 
  test with known good Twilio test credentials

**Task 4 subtasks (api/webhooks.py):**
- Separate subtask for X-Forwarded-Proto handling
- Must reconstruct URL as https:// when behind proxy/ngrok
- Acceptance: works with both direct and proxied requests

**Task 5 subtasks (tools.py update):**
- Lazy import pattern to avoid circular dependency
- 122 existing tests must pass after change
- Run pytest immediately after this subtask

## RULES
- Work in /home/ps_qasim/projects/crm-digital-fte
- Tasks breakdown only — no implementation yet
- Commit when done, do NOT push

## WHEN DONE
Confirm: tasks file path + total subtask count + all HIGH RISK 
subtasks listed with acceptance criteria.
Ready for sp.implement: yes/no

## Response snapshot

Generated `specs/006-production-agent/tasks-4c-channel-handlers.md` with 49 tasks across 6 phases:

- **Phase 1** (T001–T002): Setup — requirements.txt + .env.example
- **Phase 2** (T003–T006): Foundational — Kafka producer singleton (shared blocking dependency)
- **Phase 3** (T007–T026): US1 — Gmail handler + 10 tests + webhook endpoint + reconstruct_url
- **Phase 4** (T027–T042): US2 — WhatsApp handler + 10 tests + webhook endpoint
- **Phase 5** (T043–T045): US3 — Fault isolation audit + 122-test regression gate
- **Phase 6** (T046–T049): Polish — send_response wiring with lazy imports + final regression gate

10 HIGH RISK tasks identified with explicit acceptance criteria. 122-test gate at T045 and T049.

## Outcome

- ✅ Impact: 49-task breakdown generated for Phase 4C-i + 4C-ii; all HIGH RISK subtasks isolated with acceptance criteria; ready for /sp.implement
- 🧪 Tests: 20 new test tasks defined (10 Gmail T007–T016, 10 WhatsApp T027–T036); 2 regression gates (T045, T049)
- 📁 Files: specs/006-production-agent/tasks-4c-channel-handlers.md (NEW, 49 tasks)
- 🔁 Next prompts: /sp.implement — start with T001–T006 (setup + foundational), then T017–T026 (Gmail), then T037–T042 (WhatsApp)
- 🧠 Reflection: Lazy import pattern in T047 is the highest-complexity subtask — circular import risk from tools.py → gmail_handler.py → kafka_producer.py → models.py chain

## Evaluation notes (flywheel)

- Failure modes observed: none — task breakdown only
- Graders run and results (PASS/FAIL): n/a (no implementation run)
- Prompt variant (if applicable): n/a
- Next experiment (smallest change to try): Start T001 and run prerequisites check to confirm aiokafka installs cleanly with existing stack
