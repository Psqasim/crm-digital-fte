---
id: 001
title: CRM FTE Project Constitution
stage: constitution
date: 2026-04-01
surface: agent
model: claude-sonnet-4-6
feature: none
branch: main
user: Muhammad Qasim
command: /sp.constitution
labels: ["constitution","phase-1","nexaflow","crm","multi-channel","fte"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - .specify/memory/constitution.md
  - history/prompts/constitution/001-crm-fte-project-constitution.constitution.prompt.md
tests:
  - none
---

## Prompt

 ## CONTEXT
Project: CRM Digital FTE Factory — GIAIC Hackathon 5
Location: /home/ps_qasim/projects/crm-digital-fte
Company: NexaFlow (B2B SaaS workflow automation, 3,000 customers)
Phase: 1 — Constitution (Spec-Kit Plus)

Phase 0 is complete. The project scaffold, all context files, and GitHub repo exist.
The hackathon document is at: ./The CRM Digital FTE Factory Final Hackathon 5.md

## TASK
Run the Spec-Kit Plus constitution command: /sp.constitution

Before writing the constitution, READ these files completely:
1. ./The CRM Digital FTE Factory Final Hackathon 5.md  ← PRIMARY source, read this FULLY
2. ./context/company-profile.md
3. ./context/product-docs.md
4. ./context/escalation-rules.md
5. ./context/brand-voice.md
6. ./CLAUDE.md

The constitution must cover the ENTIRE project scope — both Stage 1 (Incubation) and
Stage 2 (Specialization). It must reflect the real hackathon scoring rubric.

The constitution must include these sections:

### 1. Project Purpose
### 2. The Digital FTE Definition
### 3. Multi-Channel Architecture Principles
### 4. Agent Principles (Non-Negotiable Rules)
### 5. Escalation Contract
### 6. Technology Stack Decisions (Locked)
### 7. Scoring-Driven Priorities (from hackathon rubric — 100 pts total)
### 8. Incubation Phase Contract (Stage 1)
### 9. Production Phase Contract (Stage 2)
### 10. Definition of Done

## RULES
- Work in /home/ps_qasim/projects/crm-digital-fte
- READ the hackathon document fully before writing — do not skim
- Constitution must be saved to .specify/memory/constitution.md
- After constitution is written, commit and push to GitHub

## EXPECTED OUTPUT
- .specify/memory/constitution.md created with all 10 sections
- Committed and pushed to GitHub

## Response snapshot

Constitution written to `.specify/memory/constitution.md` at v1.0.0. All 10 required sections
populated from full read of hackathon document, company-profile.md, product-docs.md,
escalation-rules.md, brand-voice.md, and CLAUDE.md.

Key content:
- 6 Core Principles covering: Project Purpose, Digital FTE Definition ($1K/yr vs $75K/yr human),
  Multi-Channel Architecture (III-1 through III-5 rules), Agent Behavioral Contract (ALWAYS/NEVER
  rules with datetime injection requirement), Escalation Contract (8 triggers + logging spec),
  Technology Stack (locked: OpenAI SDK, FastAPI, Neon PostgreSQL+pgvector, Kafka, Next.js 15,
  Docker+K8s, Twilio, Gmail API).
- Section 2: Full 100-point scoring rubric with "Done" definitions per criterion; Incubation Phase
  Contract (9 deliverables); Production Phase Contract (10 components with acceptance criteria).
- Section 3: Definition of Done — 24-hour multi-channel test with volume, reliability, performance,
  and quality targets.
- Governance: amendment procedure, versioning policy, compliance gate, PHR requirement.
- Sync Impact Report in HTML comment at top of file.

Version bump: (blank template) → 1.0.0 (MINOR — initial population from blank template).

## Outcome

- ✅ Impact: Project constitution established as authoritative source for all development decisions
- 🧪 Tests: No tests applicable for constitution artifact
- 📁 Files: .specify/memory/constitution.md (created/populated)
- 🔁 Next prompts: /sp.specify (Phase 2A — Initial Exploration / feature specification)
- 🧠 Reflection: Constitution covers both Stage 1 and Stage 2 fully; scoring rubric embedded to drive priority decisions; technology stack locked to prevent drift

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): no graders applicable
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): run /sp.specify for Phase 2A exploration
