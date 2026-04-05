---
id: "0011"
title: Phase 4C-iii Web Form Plan
stage: plan
date: 2026-04-05
surface: agent
model: claude-sonnet-4-6
feature: 006-production-agent
branch: 006-production-agent
user: Muhammad Qasim
command: /sp.plan
labels: ["plan","nextjs","web-form","phase-4c","frontend","fastapi","channel"]
links:
  spec: specs/006-production-agent/spec-4c-web-form.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/006-production-agent/plan-4c-web-form.md
  - specs/006-production-agent/research-4c-web-form.md
  - specs/006-production-agent/contracts/web-form-api.md
tests:
  - null
---

## Prompt

## CONTEXT
Project: CRM Digital FTE Factory — GIAIC Hackathon 5
Location: /home/ps_qasim/projects/crm-digital-fte
Branch: 006-production-agent
Phase: 4C-iii — Next.js Web Form

Spec: specs/006-production-agent/spec-4c-web-form.md
4 pages: / (landing), /support (form), /ticket/[id] (status), /dashboard (metrics)
Key constraint: FastAPI needs 3 new endpoints BEFORE Next.js proxy works:
- POST /support/submit
- GET /support/ticket/{ticket_id}
- GET /metrics/summary

Frontend location: src/web-form/ (own package.json)

[Full prompt included 6 blocks of design decisions: FastAPI endpoints, Next.js scaffold,
shared components, proxy routes, pages, and polish with HIGH RISK flagging instructions]

## Response snapshot

Generated 3 artifacts:
1. `specs/006-production-agent/plan-4c-web-form.md` — main plan with 6 blocks, ~30 tasks
2. `specs/006-production-agent/research-4c-web-form.md` — 10 research items (R-001 to R-010)
3. `specs/006-production-agent/contracts/web-form-api.md` — full API contracts

Research highlights: create-next-app subdirectory pattern, shadcn init workflow, canvas-confetti
types, next-themes dark-default, 5s polling with setInterval, TKT-XXX from UUID substring,
priority ALTER TABLE migration, Framer Motion client-only constraint, asyncpg pool reuse,
404 passthrough from FastAPI proxy.

Constitution check passed: PKT datetime, secrets policy, Kafka unified ingestion, channel
metadata preservation, Pydantic v2, Rule III-5 web form priority.

Plan structure:
- Block 1: FastAPI endpoints — 5 tasks (B1-T1 to B1-T5); includes DB migration for priority column
- Block 2: Next.js scaffold — 4 tasks (B2-T1 to B2-T4)
- Block 3: Shared components — 5 tasks (B3-T1 to B3-T5)
- Block 4: Proxy routes — 3 tasks (B4-T1 to B4-T3)
- Block 5: Pages — 4 tasks (B5-T1 to B5-T4)
- Block 6: Polish — 5 tasks (B6-T1 to B6-T5)

HIGH RISK tasks: B1-T3 (multi-step DB pipeline), B2-T1 (scaffold exact command), B5-T2 (RHF+Zod+confetti), B5-T3 (polling lifecycle)

## Outcome

- ✅ Impact: Complete plan for Phase 4C-iii. 6 blocks, ~30 tasks, 4 HIGH RISK tasks identified.
  FastAPI priority column migration (R-007) is a key discovery — not in existing schema.
- 🧪 Tests: No tests in planning phase
- 📁 Files: plan-4c-web-form.md, research-4c-web-form.md, contracts/web-form-api.md
- 🔁 Next prompts: /sp.tasks for Phase 4C-iii
- 🧠 Reflection: setup-plan.sh overwrote existing plan.md with template — restored via git checkout.
  This is a known script limitation when run on an already-planned feature. The web-form plan
  correctly lives at plan-4c-web-form.md following the Phase 4C naming convention.

## Evaluation notes (flywheel)

- Failure modes observed: setup-plan.sh clobbered plan.md (restored via git checkout)
- Graders run and results (PASS/FAIL): constitution check — all PASS
- Prompt variant (if applicable): sp.plan with explicit 6-block user-defined structure
- Next experiment (smallest change to try): Run /sp.tasks — start with Block 1 FastAPI tasks (hard dependency)
