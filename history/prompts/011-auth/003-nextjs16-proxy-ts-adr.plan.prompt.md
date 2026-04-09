---
id: "003"
title: "Next.js 16 proxy.ts ADR"
stage: plan
date: 2026-04-09
surface: agent
model: claude-sonnet-4-6
feature: 011-auth
branch: 011-auth
user: Muhammad Qasim
command: /sp.adr next-js-16-upgrade
labels: ["adr", "next-js-16", "proxy.ts", "auth", "runtime"]
links:
  spec: specs/011-auth/spec.md
  ticket: null
  adr: history/adr/0004-next-js-16-upgrade-and-proxy-ts-route-protection.md
  pr: null
files:
  - history/adr/0004-next-js-16-upgrade-and-proxy-ts-route-protection.md
tests:
  - null
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
Do things in order:

### Part A — ADR first
/sp.adr next-js-16-upgrade
Document: Next.js 16.2.2 installed vs 15 in constitution.
Key changes: proxy.ts rename, Node.js runtime default, Turbopack default.
Impact on auth implementation.

## RULES
- Work in /home/ps_qasim/projects/crm-digital-fte
- Commit, do NOT push

## WHEN DONE
Confirm: ADR path.
Ready for sp.task: yes/no

## Response snapshot

Created ADR-0004 documenting the Next.js 16 upgrade decision for Phase 7A.

Decision: Use Next.js 16.2.2 as-is with proxy.ts (Node.js runtime). No downgrade.

Key tradeoffs documented:
- Positive: Eliminates Edge runtime restrictions for bcryptjs + Neon client; Turbopack dev speed; simpler auth setup
- Negative: proxy.ts rename breaks middleware.ts expectations; constitution §VI version drift; next-auth@beta + Next.js 16 compatibility not explicitly documented; must pin beta version
- 4 alternatives considered: downgrade to 15.x, Edge runtime, custom JWT auth, middleware.ts shim
- All rejected with rationale

Significance test: PASS (all 3 criteria met — cross-cutting, alternatives considered, long-term platform impact)

ADR-0004 path: history/adr/0004-next-js-16-upgrade-and-proxy-ts-route-protection.md

## Outcome

- ✅ Impact: Architecturally significant platform decision documented; team can proceed with proxy.ts naming with confidence
- 🧪 Tests: No tests (ADR stage)
- 📁 Files: history/adr/0004-next-js-16-upgrade-and-proxy-ts-route-protection.md
- 🔁 Next prompts: /sp.tasks for Phase 7A
- 🧠 Reflection: The proxy.ts rename is the highest-risk naming issue in the entire auth implementation. Having it documented in an ADR ensures it won't be accidentally reverted or misunderstood.

## Evaluation notes (flywheel)

- Failure modes observed: create-adr.sh requires --title flag (not positional arg) — noted for future use
- Graders run and results (PASS/FAIL): Significance test PASS (impact ✅, alternatives ✅, cross-cutting ✅); Measure checklist PASS
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): null
