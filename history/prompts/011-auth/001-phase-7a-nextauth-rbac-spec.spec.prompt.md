---
id: "001"
title: "Phase 7A NextAuth RBAC Spec"
stage: spec
date: 2026-04-09
surface: agent
model: claude-sonnet-4-6
feature: 011-auth
branch: 011-auth
user: Muhammad Qasim
command: /sp.specify
labels: ["auth", "rbac", "next-auth", "jwt", "spec"]
links:
  spec: specs/011-auth/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/011-auth/spec.md
  - specs/011-auth/checklists/requirements.md
tests:
  - null
---

## Prompt

## CONTEXT
Project: CRM Digital FTE Factory — GIAIC Hackathon 5
Location: /home/ps_qasim/projects/crm-digital-fte
Frontend: src/web-form/ (Next.js 15, app router, TypeScript, Tailwind, shadcn/ui)
Backend: FastAPI on HF Spaces (https://psqasim-crm-digital-fte-api.hf.space)
Database: Neon PostgreSQL (existing 8 tables)

Phase: 7A — NextAuth.js v5 Auth + RBAC

Auth requirements:
- Public users: landing page + /support form — NO login needed
- /login page — internal only, no public signup
- Roles: admin | agent (enum)
- Admin: sees /admin/dashboard — all tickets, user management, create accounts
- Agent: sees /dashboard — assigned tickets only
- Not logged in + tries /dashboard or /admin/* → redirect to /login
- JWT strategy (not DB sessions)
- Seed script: admin@nexaflow.com / Admin123!
- JWT secret shared with FastAPI backend

Read before specifying:
- src/web-form/app/ structure (existing pages)
- .claude/skills/nextjs-16-skill/ (read fully)
- specs/customer-success-fte-spec.md

## MANDATORY — USE CONTEXT7 BEFORE SPECIFYING
Search:
1. "next-auth v5 app router credentials provider jwt"
2. "next-auth v5 middleware matcher protected routes"
3. "next-auth v5 session jwt callback role"

Do NOT write spec until confirmed.

## TASK
Run /sp.specify for Phase 7A.

Scope:
- users table in Neon (id, name, email, hashed_password, role, created_at)
- NextAuth.js v5 Credentials provider
- JWT with role claim
- Middleware: protect /dashboard, /admin/* → redirect /login
- /login page (shadcn form, Zod validation, dark theme)
- /admin/dashboard — all tickets table + create user form
- /dashboard — update to show only assigned/all tickets with auth guard
- seed.ts script creates default admin
- Navbar: shows Login button if not authed, 
  shows role-based links if authed + Logout

## RULES
- Work in /home/ps_qasim/projects/crm-digital-fte
- New branch: 011-auth
- Specify only — no code yet
- Commit when done, do NOT push

## WHEN DONE
Confirm: spec file path. Ready for sp.plan: yes/no

## Response snapshot

Created branch `011-auth` and wrote full specification for Phase 7A NextAuth.js v5 Auth + RBAC.

Key spec decisions:
- 5 user stories: login flow, route protection, admin user management, agent dashboard, navbar state
- 27 functional requirements across: authentication, route protection, login page, admin dashboard, agent dashboard, navbar, seeding
- Confirmed Next.js 16.2.2 is installed (proxy.ts replaces middleware.ts per Context7 docs)
- JWT strategy with role claim; AUTH_SECRET shared with FastAPI
- Users table: id, name, email, hashed_password, role (admin|agent), created_at
- Seed: admin@nexaflow.com / Admin123! (idempotent)
- Public routes (/, /support, /ticket/*) remain unprotected
- Admin creates accounts; no public signup
- All checklist items passed

Spec at: specs/011-auth/spec.md
Checklist at: specs/011-auth/checklists/requirements.md

## Outcome

- ✅ Impact: Full auth + RBAC specification written, branch created, ready for /sp.plan
- 🧪 Tests: No tests at spec stage
- 📁 Files: specs/011-auth/spec.md, specs/011-auth/checklists/requirements.md
- 🔁 Next prompts: /sp.plan for Phase 7A
- 🧠 Reflection: Next.js 16 proxy.ts discovery is important — the AGENTS.md in web-form warns about breaking changes. Context7 confirmed middleware.ts → proxy.ts rename.

## Evaluation notes (flywheel)

- Failure modes observed: Context7 tools were denied in sub-agent; had to use directly in main conversation
- Graders run and results (PASS/FAIL): Spec quality checklist — all 12 items PASS
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): null
