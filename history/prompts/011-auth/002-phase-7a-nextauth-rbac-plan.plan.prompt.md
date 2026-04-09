---
id: "002"
title: "Phase 7A NextAuth RBAC Plan"
stage: plan
date: 2026-04-09
surface: agent
model: claude-sonnet-4-6
feature: 011-auth
branch: 011-auth
user: Muhammad Qasim
command: /sp.plan
labels: ["auth", "rbac", "next-auth", "jwt", "plan", "proxy.ts", "bcryptjs"]
links:
  spec: specs/011-auth/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/011-auth/plan.md
  - specs/011-auth/research.md
  - specs/011-auth/data-model.md
  - specs/011-auth/quickstart.md
  - specs/011-auth/contracts/POST_api_admin_users.md
  - specs/011-auth/contracts/GET_POST_api_auth_nextauth.md
  - CLAUDE.md
tests:
  - null
---

## Prompt

## CONTEXT
Project: CRM Digital FTE Factory — GIAIC Hackathon 5
Location: /home/ps_qasim/projects/crm-digital-fte
Branch: 011-auth
Phase: 7A — NextAuth.js v5 Auth + RBAC

Spec: specs/011-auth/spec.md (12/12 checklist pass)
Key decisions:
- Next.js 16.2.2 installed — middleware file is proxy.ts NOT middleware.ts
- JWT strategy, no DB sessions
- Roles: admin | agent
- Protected: /dashboard, /admin/* → /login
- Public: /, /support, /ticket/*
- Users table needs migration on Neon
- Seed: admin@nexaflow.com / Admin123!

## MANDATORY — USE CONTEXT7 BEFORE PLANNING
Search:
1. "next-auth v5 credentials provider authorize callback"
2. "next-auth v5 session jwt callbacks role custom field"
3. "bcryptjs hash compare password nodejs"

## TASK
Run /sp.plan for Phase 7A.

Plan must cover these components in order:

Block 1 — Database: 004_add_users_table.sql, queries.py updates, seed.ts
Block 2 — NextAuth.js setup: auth.ts, auth.config.ts, types/next-auth.d.ts
Block 3 — Route protection: proxy.ts (NOT middleware.ts — Next.js 16)
Block 4 — Login page: /login with shadcn form, Zod, dark theme
Block 5 — Admin dashboard: /admin/dashboard, /api/admin/users
Block 6 — Update /dashboard: auth guard, user badge
Block 7 — Navbar: auth-aware links
Block 8 — API routes: /api/admin/users, /api/auth/[...nextauth]

Flag HIGH RISK tasks.

## RULES
- Work in /home/ps_qasim/projects/crm-digital-fte
- Planning only — no code yet
- proxy.ts NOT middleware.ts (Next.js 16)
- Commit when done, do NOT push

## WHEN DONE
Confirm: plan file path + task count + HIGH RISK tasks.
Ready for sp.tasks: yes/no

## Response snapshot

Created full implementation plan for Phase 7A with 8 blocks, 6 supporting artifacts, and agent context updated.

Key planning decisions:
- proxy.ts (not middleware.ts) confirmed by Context7 — Next.js 16 rename
- Split auth.ts / auth.config.ts pattern per NextAuth v5 best practices
- @neondatabase/serverless for Next.js DB queries (same Neon instance, no ORM)
- bcryptjs with cost factor 12 (async hash/compare pattern confirmed)
- JWT role in token via jwt/session callbacks + next-auth.d.ts type augmentation
- Implementation order: DB → NextAuth setup → Seed → proxy.ts → Login → Admin Dashboard → /dashboard → Navbar
- HIGH RISK blocks: B2 (next-auth@beta compatibility), B3 (proxy.ts silent failure), B5 (dual data sources)
- ADR suggestion issued for Next.js 15→16 upgrade

Artifacts created:
- specs/011-auth/plan.md (8 blocks, risk register, env vars, implementation order)
- specs/011-auth/research.md (8 research decisions, all Context7-verified)
- specs/011-auth/data-model.md (users table schema, Python queries.py, TypeScript lib/db.ts)
- specs/011-auth/quickstart.md (step-by-step setup guide)
- specs/011-auth/contracts/POST_api_admin_users.md
- specs/011-auth/contracts/GET_POST_api_auth_nextauth.md

## Outcome

- ✅ Impact: Complete implementation plan committed; ready for /sp.tasks
- 🧪 Tests: No tests at plan stage
- 📁 Files: 7 files created/modified
- 🔁 Next prompts: /sp.tasks for Phase 7A
- 🧠 Reflection: Context7 confirmed proxy.ts rename for Next.js 16. The split auth.ts/auth.config.ts pattern is important — keeping providers-only config separate allows future Edge compatibility.

## Evaluation notes (flywheel)

- Failure modes observed: None — Context7 tools available directly in main conversation
- Graders run and results (PASS/FAIL): Constitution Check — all gates PASS (with one NOTE on Next.js version mismatch)
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): null
