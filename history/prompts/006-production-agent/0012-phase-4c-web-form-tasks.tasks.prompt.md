---
id: "0012"
title: Phase 4C-iii Web Form Tasks
stage: tasks
date: 2026-04-05
surface: agent
model: claude-sonnet-4-6
feature: 006-production-agent
branch: 006-production-agent
user: Muhammad Qasim
command: /sp.tasks
labels: ["tasks","nextjs","fastapi","web-form","phase-4c-iii","high-risk"]
links:
  spec: specs/006-production-agent/spec-4c-web-form.md
  ticket: "null"
  adr: "null"
  pr: "null"
files:
  - specs/006-production-agent/tasks-4c-web-form.md
tests:
  - "T036: pytest tests/ production/tests/ -v — must show 142 passed, 0 failed"
---

## Prompt

## CONTEXT
Project: CRM Digital FTE Factory — GIAIC Hackathon 5
Location: /home/ps_qasim/projects/crm-digital-fte
Branch: 006-production-agent
Phase: 4C-iii — Next.js Web Form

Plan: specs/006-production-agent/plan-4c-web-form.md
26 tasks across 6 blocks
HIGH RISK: B1-T3 (DB pipeline), B2-T1 (scaffold), B5-T2 (form), B5-T3 (polling)
Key: ALTER TABLE adds priority column (backwards compatible)
Current Python tests: 142 passing — must stay green

## TASK
Run /sp.tasks for Phase 4C-iii.

Break all 26 tasks into individual implementable subtasks.
Each must have:
- Exact file to create/modify
- Acceptance criteria
- Dependencies
- Test needed: yes/no
- HIGH RISK flag

Special attention per HIGH RISK task:

**B1-T3 — web_form_handler submit_ticket (HIGH RISK):**
Break into subtasks:
- Subtask A: get_or_create_customer (with rollback plan if fails)
- Subtask B: create_conversation 
- Subtask C: add_message
- Subtask D: create_ticket (with priority field)
- Subtask E: publish to Kafka "fte.tickets.incoming"
- Subtask F: return ticket_id + estimated_response_time
Acceptance: if any DB step fails → rollback all, return 500 with clear error
Test: mock DB pool, verify all 6 steps called in order

**B2-T1 — Next.js scaffold (HIGH RISK):**
Exact command to use:
cd src/web-form && npx create-next-app@latest . \
  --typescript --tailwind --eslint --app \
  --no-git --import-alias "@/*"
Then verify: src/web-form/app/layout.tsx exists
Acceptance: npm run dev starts without error on port 3001
(port 3000 may be taken — use PORT=3001)

**B5-T2 — Support form (HIGH RISK):**
Break into subtasks:
- Subtask A: Zod schema definition (all 6 fields with constraints)
- Subtask B: RHF useForm setup with zodResolver
- Subtask C: Form UI (all fields, shadcn components, dark theme)
- Subtask D: Optimistic submit handler
- Subtask E: canvas-confetti trigger (fire after success, duration 2s, NexaFlow blue colors #3B82F6)
- Subtask F: Framer Motion field entrance animations

**B5-T3 — Ticket status polling (HIGH RISK):**
Break into subtasks:
- Subtask A: useEffect polling setup with setInterval
- Subtask B: cleanup on unmount (clearInterval in return function)
- Subtask C: stop polling when status=resolved or status=escalated
- Subtask D: typing indicator ("AI is analyzing your ticket...")
- Subtask E: skeleton loader on initial load (before first fetch)
- Subtask F: not-found state when ticket ID invalid

**On Python regression gate:**
After B1 (all FastAPI tasks) — run:
pytest tests/ production/tests/ -v
Must show 142 passed, 0 failed before touching any frontend

## RULES
- Work in /home/ps_qasim/projects/crm-digital-fte
- Tasks breakdown only — no implementation yet
- Commit when done, do NOT push

## WHEN DONE
Confirm: tasks file path + total subtask count + all HIGH RISK 
subtasks listed with acceptance criteria.
Ready for sp.implement: yes/no

## Response snapshot

Generated `specs/006-production-agent/tasks-4c-web-form.md` with 100 tasks across 7 phases organized by user story.

Phase breakdown: Phase 1 (DB migration, 4 tasks) → Phase 2 (Python queries + Next.js scaffold + 15 shared components, 32 tasks including T036 regression gate) → Phase 3 (US1 form submission HIGH RISK, 24 tasks) → Phase 4 (US2 ticket polling HIGH RISK, 11 tasks) → Phase 5 (US3 dashboard, 6 tasks) → Phase 6 (US4 landing, 3 tasks) → Phase 7 (polish, 20 tasks).

HIGH RISK decomposition: B1-T3 → T038–T044 (6 pipeline subtasks A–F + try/except); B2-T1 → T007+T010 (exact scaffold command + dev server verify); B5-T2 → T052–T059 (Zod schema, RHF setup, form UI, character counter, optimistic handler, confetti, disabled state, a11y); B5-T3 → T065–T071 (polling, cleanup, stop conditions, typing indicator, skeleton, not-found).

## Outcome

- ✅ Impact: 100 individually implementable tasks with exact file paths, acceptance criteria, dependencies, and HIGH RISK flags; T036 hard gate between Python and frontend work
- 🧪 Tests: T036 regression gate (pytest 142 tests); no new test files
- 📁 Files: specs/006-production-agent/tasks-4c-web-form.md (created, 100 tasks)
- 🔁 Next prompts: /sp.implement for Phase 4C-iii
- 🧠 Reflection: B1-T3 6-step pipeline split into atomic subtasks with explicit Kafka-failure semantics (best-effort, does not raise); B5-T2 and B5-T3 fully match user's subtask A–F specifications

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): T036 gate not yet run (tasks only phase)
- Prompt variant (if applicable): sp.tasks with HIGH RISK decomposition context
- Next experiment: run sp.implement with T036 gate as mandatory checkpoint
