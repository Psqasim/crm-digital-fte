---
id: "0010"
title: Phase 4C-iii Web Form Spec
stage: spec
date: 2026-04-05
surface: agent
model: claude-sonnet-4-6
feature: 006-production-agent
branch: 006-production-agent
user: Muhammad Qasim
command: /sp.specify
labels: ["spec","nextjs","web-form","phase-4c","frontend","channel"]
links:
  spec: specs/006-production-agent/spec-4c-web-form.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/006-production-agent/spec-4c-web-form.md
  - specs/006-production-agent/checklists/requirements-4c-web-form.md
tests:
  - null
---

## Prompt

## CONTEXT
Project: CRM Digital FTE Factory — GIAIC Hackathon 5
Location: /home/ps_qasim/projects/crm-digital-fte
Branch: 006-production-agent
Phase: 4C-iii — Next.js Web Support Form (10 points — highest single rubric item)

This is NOT a minimal hackathon form. This is a portfolio-grade production 
frontend for NexaFlow — a fictional B2B SaaS company. It will be shared on 
LinkedIn and must look like a real product.

Read these before specifying:
- ./The CRM Digital FTE Factory Final Hackathon 5.md (Web Form requirements)
- .claude/skills/nextjs-16-skill/ (read FULLY before writing spec)
- specs/customer-success-fte-spec.md (§2 channel specs, §7 performance)
- context/company-profile.md (NexaFlow brand details)
- context/brand-voice.md (tone)
- production/api/main.py (FastAPI endpoints the form will call — check what exists)

## MANDATORY — USE CONTEXT7 BEFORE SPECIFYING
Search ALL of these now:
1. "next.js 15 app router layout metadata generateMetadata"
2. "shadcn ui form react hook form zod validation"
3. "framer motion next.js page transitions entrance animation"
4. "next.js 15 api route proxy backend"
Do NOT write spec until all 4 confirmed.

## TASK
Run /sp.specify for Phase 4C-iii.

## DESIGN DECISIONS (locked — do not deviate):
[Brand, Pages x4, Technical requirements, Location — all detailed in prompt]

## RULES
- Work in /home/ps_qasim/projects/crm-digital-fte
- Read nextjs-16-skill FULLY before writing spec
- Context7 must be confirmed before spec is written
- Specify only — no code yet
- Commit when done, do NOT push

## Response snapshot

Executed /sp.specify for Phase 4C-iii. Read all required context files (company-profile.md,
brand-voice.md, hackathon brief, nextjs-16-skill/ all reference files, web_form_handler.py,
existing spec-4c-channel-handlers.md). Confirmed all 4 Context7 queries (generateMetadata,
shadcn RHF Zod, Framer Motion entrance animations, Next.js API proxy pattern).

Wrote spec to: specs/006-production-agent/spec-4c-web-form.md
- 4 user stories (P1-P4): form submission, ticket tracking, dashboard, landing page
- 25 functional requirements (FR-001 to FR-025) covering all 4 pages
- 3 key entities: Ticket, Form Submission, Metrics Snapshot
- 8 success criteria (SC-001 to SC-008) including Lighthouse 90+, keyboard nav, mobile 375px
- Out of Scope section (no auth, no file upload, no email notifications)
- Dependencies section (FastAPI 3 new endpoints, Kafka, PostgreSQL)
- Context7 findings documented inline

Created checklist: specs/006-production-agent/checklists/requirements-4c-web-form.md
All checklist items pass. No [NEEDS CLARIFICATION] markers.

## Outcome

- ✅ Impact: Complete spec for Phase 4C-iii covering all 4 pages, 25 FRs, 8 success criteria.
  FastAPI endpoint requirements (FR-025) explicitly called out as a hard dependency.
- 🧪 Tests: No tests in this phase (spec-only)
- 📁 Files: specs/006-production-agent/spec-4c-web-form.md, specs/006-production-agent/checklists/requirements-4c-web-form.md
- 🔁 Next prompts: /sp.plan for Phase 4C-iii
- 🧠 Reflection: Stayed on 006-production-agent branch per user intent (sub-phase, not new feature).
  All Context7 queries confirmed before spec was written. FastAPI stub (web_form_handler.py is empty)
  surfaced as key dependency — plan phase must account for it.

## Evaluation notes (flywheel)

- Failure modes observed: None — all required files read, all Context7 searches confirmed
- Graders run and results (PASS/FAIL): checklist at requirements-4c-web-form.md — all PASS
- Prompt variant (if applicable): sp.specify with locked design decisions
- Next experiment (smallest change to try): Run /sp.plan with FastAPI endpoint design as first task
