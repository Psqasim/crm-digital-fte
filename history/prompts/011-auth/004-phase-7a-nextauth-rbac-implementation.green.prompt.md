---
id: "004"
title: Phase 7A NextAuth.js v5 RBAC Implementation
stage: green
date: 2026-04-10
surface: agent
model: claude-sonnet-4-6
feature: 011-auth
branch: 011-auth
user: Muhammad Qasim
command: /sp.implement
labels: ["nextauth", "rbac", "auth", "next.js-16", "proxy.ts", "implementation"]
links:
  spec: specs/011-auth/spec.md
  ticket: null
  adr: history/adr/ADR-0004-nextjs16-proxy.md
  pr: https://github.com/Psqasim/crm-digital-fte/pull/10
files:
  - production/database/migrations/004_add_users_table.sql
  - production/database/queries.py
  - src/web-form/auth.config.ts
  - src/web-form/auth.ts
  - src/web-form/proxy.ts
  - src/web-form/types/next-auth.d.ts
  - src/web-form/lib/db.ts
  - src/web-form/app/login/page.tsx
  - src/web-form/app/login/LoginForm.tsx
  - src/web-form/app/admin/dashboard/page.tsx
  - src/web-form/app/admin/dashboard/AdminDashboardContent.tsx
  - src/web-form/app/api/auth/[...nextauth]/route.ts
  - src/web-form/app/api/admin/users/route.ts
  - src/web-form/scripts/seed.ts
  - src/web-form/app/dashboard/page.tsx
  - src/web-form/app/dashboard/DashboardContent.tsx
  - src/web-form/components/Navbar.tsx
  - specs/011-auth/tasks.md
tests:
  - proxy.ts smoke test 1: /dashboard → 307 /login PASS
  - proxy.ts smoke test 2: /admin/dashboard → 307 /login PASS
  - proxy.ts smoke test 3: / → 200 PASS
  - proxy.ts smoke test 4: /support → 200 PASS
  - npm run build: 0 TypeScript errors, 0 build errors PASS
  - seed script idempotent: run 1 creates, run 2 skips PASS
  - DB migration 004_add_users_table.sql: exits 0 PASS
---

## Prompt

## CONTEXT
Project: CRM Digital FTE Factory — GIAIC Hackathon 5
Location: /home/ps_qasim/projects/crm-digital-fte
Branch: 011-auth
Phase: 7A — NextAuth.js v5 Auth + RBAC

Tasks: specs/011-auth/tasks.md (23 tasks)
HIGH RISK: T005, T007, T008, T009, T014
Next.js version: 16.2.2 — use proxy.ts NOT middleware.ts
Current tests: 166 passing

## MANDATORY — USE CONTEXT7 BEFORE ANY CODE
Search:
1. "next-auth v5 beta credentials provider nextjs 16"
2. "next-auth v5 auth.ts auth.config.ts split configuration"
3. "next-auth v5 proxy.ts route protection matcher"
Do NOT write code until confirmed.
Also read: .claude/skills/nextjs-16-skill/ fully

## TASK
Run /sp.implement for all 23 tasks T001 → T023.

[HIGH RISK rules for T005, T007, T008, T009, T014 provided in full]
[Admin dashboard, navbar, smoke tests, final build check instructions provided]

## RULES
- Work in /home/ps_qasim/projects/crm-digital-fte
- proxy.ts NOT middleware.ts — this is non-negotiable
- Context7 confirmed before any auth code
- Run npm run build after T005, T008, T014
- After ALL 23 tasks: full build must pass
- Commit: "feat: Phase 7A — NextAuth.js v5 RBAC, login, admin dashboard"
- Push branch 011-auth
- GitHub MCP: PR + merge to main, keep branch

## Response snapshot

All 23 tasks implemented and verified:

**T001–T002**: package.json verified (next-auth absent), AUTH_SECRET generated and added to .env.local + .env.example. DATABASE_URL pulled from root .env and added to web-form .env.local.

**T003–T004** (parallel): `004_add_users_table.sql` migration created (idempotent IF NOT EXISTS). `get_user_by_email()` and `create_user()` appended to `production/database/queries.py`.

**T005**: `next-auth@5.0.0-beta.30`, `bcryptjs@3.0.3`, `@types/bcryptjs`, `@neondatabase/serverless@1.0.2` installed. `npm run build` passed.

**T006**: `lib/db.ts` — Neon serverless client with `getUserByEmail()` and `createUser()`.

**T007**: `auth.config.ts` — Edge-safe, bcrypt imported inside `authorize()` body (not module-level).

**T008**: `auth.ts` — `NextAuth({ ...authConfig, session: { strategy: 'jwt' }, callbacks: { jwt, session } })`. Exports `{ handlers, auth, signIn, signOut }`.

**T009**: `types/next-auth.d.ts` — augments Session/JWT/User with `role: string`, `id: string`.

**T010**: `app/api/auth/[...nextauth]/route.ts` — `export const { GET, POST } = handlers`.

**T011**: `scripts/seed.ts` — idempotent admin seed. Run 1: "✅ Admin user created". Run 2: "ℹ️ Admin user already exists — skipping".

**T012–T013**: `/login/page.tsx` (Server Component, redirects if session) + `LoginForm.tsx` (Client Component, react-hook-form + zod + signIn + role-based redirect).

**T014**: `proxy.ts` (NOT middleware.ts). 4 smoke tests passed: /dashboard → 307 /login, /admin/dashboard → 307 /login, / → 200, /support → 200.

**T015–T016** (parallel): `/admin/dashboard/page.tsx` + `AdminDashboardContent.tsx` — tickets table from FastAPI + Create User form.

**T017**: `/api/admin/users/route.ts` — session role gate, bcrypt hash, `createUser()`, 409 on duplicate.

**T018–T019** (parallel): Dashboard `page.tsx` + `DashboardContent.tsx` updated with `auth()` guard and user name/role badge.

**T020**: `Navbar.tsx` converted to async Server Component — Login (unauthenticated), Admin Dashboard link (admin), Dashboard link (agent), Server Action logout.

**T021–T022**: `npm run build` — 0 TypeScript errors, 0 build errors, 12 routes, proxy registered. DB migration + seed both succeeded.

**T023**: Committed `feat(auth): Phase 7A — NextAuth.js v5 RBAC, login, admin dashboard` (20 files, 1082 insertions). PR #10 created and merged to main.

## Outcome

- ✅ Impact: Full NextAuth.js v5 RBAC auth stack deployed — login, route protection, admin dashboard, user management, navbar auth state
- 🧪 Tests: All 4 proxy.ts smoke tests pass; npm run build 0 errors; seed idempotent; DB migration exits 0
- 📁 Files: 13 new files created, 5 existing files updated, 20 total changes
- 🔁 Next prompts: Phase 7B (Chat Agent integration); add email/agent invite flow; session refresh; protected API routes for FastAPI
- 🧠 Reflection: Context7 confirmed proxy.ts (not middleware.ts) for Next.js 16 before any code was written. bcrypt imported inside authorize() body to maintain Edge compatibility. AUTH_SECRET and DATABASE_URL added to web-form .env.local from root .env.

## Evaluation notes (flywheel)

- Failure modes observed: none — all 23 tasks completed successfully on first attempt
- Graders run and results (PASS/FAIL): build PASS, smoke tests PASS, seed PASS, migration PASS
- Prompt variant (if applicable): sp.implement with inline HIGH RISK task instructions
- Next experiment (smallest change to try): add SESSION_MAXAGE to auth.ts for configurable token expiry
