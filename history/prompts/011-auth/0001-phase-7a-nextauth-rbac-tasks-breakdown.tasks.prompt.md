---
id: "004"
title: Phase 7A NextAuth RBAC Tasks Breakdown
stage: tasks
date: 2026-04-09
surface: agent
model: claude-sonnet-4-6
feature: 011-auth
branch: 011-auth
user: Muhammad Qasim
command: /sp.tasks
labels: ["tasks","auth","nextauth","rbac","next.js","phase-7a"]
links:
  spec: specs/011-auth/spec.md
  ticket: "null"
  adr: history/adr/ADR-0004-nextjs16-proxy-ts-node-runtime.md
  pr: "null"
files:
  - specs/011-auth/tasks.md
tests:
  - "null"
---

## Prompt

## CONTEXT
Project: CRM Digital FTE Factory — GIAIC Hackathon 5
Location: /home/ps_qasim/projects/crm-digital-fte
Branch: 011-auth
Phase: 7A — NextAuth.js v5 Auth + RBAC

Plan: specs/011-auth/plan.md (8 blocks)
HIGH RISK: B2 (next-auth@beta peer deps), B3 (proxy.ts naming)
Current tests: 166 passing — must stay green

## TASK
Break all 8 blocks into individual implementable tasks.
Each must have:
- Exact file to create/modify
- Acceptance criteria
- Dependencies
- Test needed: yes/no
- HIGH RISK flag

Special attention:

**B2 subtasks (HIGH RISK — next-auth@beta):**
- Separate subtask for install (verify no peer dep conflicts)
- Separate subtask for auth.config.ts (providers only — Edge safe)
- Separate subtask for auth.ts (full config with callbacks)
- Separate subtask for TypeScript types (extend Session + JWT)
- Acceptance: npm run build passes after each subtask

**B3 subtasks (HIGH RISK — proxy.ts):**
- Verify file is named proxy.ts NOT middleware.ts
- Test: unauthenticated GET /dashboard → 302 to /login
- Test: admin token → /admin/dashboard → 200
- Test: agent token → /admin/dashboard → 302 to /dashboard

**B5 subtasks (dual data sources):**
- Tickets data: fetch from FastAPI (existing pattern)
- User creation: POST to /api/admin/users (Next.js API route → Neon directly)
- Keep them separate — don't mix into one fetch call

## RULES
- Work in /home/ps_qasim/projects/crm-digital-fte
- Tasks breakdown only — no implementation
- Commit, do NOT push

## Response snapshot

Generated `specs/011-auth/tasks.md` with 23 tasks across 8 phases covering all 8 plan blocks.

**Structure:**
- Phase 1 Setup (T001–T002): env verification + AUTH_SECRET
- Phase 2 Foundational (T003–T011): B1 DB migration + B2 NextAuth setup (4 HIGH RISK subtasks) + B8 seed
- Phase 3 US1 Login P1 (T012–T013): B4 login page + LoginForm
- Phase 4 US2 Route Protection P2 (T014): B3 proxy.ts HIGH RISK with 4 manual smoke tests
- Phase 5 US3 Admin Dashboard P3 (T015–T017): B5 with dual data sources explicitly separated
- Phase 6 US4 Agent Dashboard P4 (T018–T019): B6 dashboard auth guard + role badge
- Phase 7 US5 Navbar P5 (T020): B7 async Server Component
- Phase 8 Polish (T021–T023): build verify + smoke tests + commit

**HIGH RISK tasks:** T005 (install), T007 (auth.config.ts), T008 (auth.ts), T009 (types), T014 (proxy.ts) = 5 tasks
**Parallel groups:** T003+T004, T015+T016, T018+T019

## Outcome

- ✅ Impact: All 8 plan blocks broken into 23 individually executable tasks; sp.implement can consume tasks.md immediately
- 🧪 Tests: No automated tests generated (spec does not request TDD); manual smoke tests specified for T005, T009, T014, T022
- 📁 Files: specs/011-auth/tasks.md (created)
- 🔁 Next prompts: /sp.implement to execute tasks sequentially
- 🧠 Reflection: B3 HIGH RISK (proxy.ts naming) placed as US2 with explicit 4-case smoke test checklist; B2 HIGH RISK split into 4 sequential subtasks each with build validation gate; B5 dual data sources documented at task level to prevent mixing

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): n/a
- Prompt variant (if applicable): n/a
- Next experiment (smallest change to try): n/a
