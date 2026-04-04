---
id: "0001"
title: Phase 2C Memory and State Spec
stage: spec
date: 2026-04-02
surface: agent
model: claude-sonnet-4-6
feature: 002-memory-state
branch: 002-memory-state
user: Muhammad Qasim
command: /sp.specify
labels: [memory, state, conversation-history, identity, sentiment-trend, ticket-status, topic-tracking]
links:
  spec: specs/002-memory-state/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/002-memory-state/spec.md
  - specs/002-memory-state/checklists/requirements.md
  - history/prompts/002-memory-state/0001-phase-2c-memory-state-spec.spec.prompt.md
tests:
  - none (spec phase — no tests)
---

## Prompt

 ## CONTEXT
Project: CRM Digital FTE Factory — GIAIC Hackathon 5
Location: /home/ps_qasim/projects/crm-digital-fte
Branch: 001-incubation-exploration
Phase: 2C — Add Memory and State

Phase 2B complete. Prototype handles single messages with no memory.
Files: src/agent/models.py, prototype.py, escalation_evaluator.py, 
channel_formatter.py, knowledge_base.py. 16/16 tests passing.

## TASK
Run /sp.specify for Phase 2C.

Scope of this phase — extend the prototype to track:
1. Conversation history (multi-turn — customer sends follow-up, agent remembers context)
2. Customer identity across channels (email as primary key, phone → email resolution)
3. Sentiment trend (not just single message — is customer getting more frustrated over time?)
4. Resolution status per ticket (open/pending/escalated/resolved)
5. Channel switches (same customer contacts via email then WhatsApp — merge history)
6. Topic tracking (what has this customer asked about before?)

All state is in-memory for now (dict/list). 
PostgreSQL comes in Phase 4A — not yet.

## RULES
- Work in /home/ps_qasim/projects/crm-digital-fte
- Specify only — no code yet
- Commit when done, do NOT push

## WHEN DONE
Confirm: spec file path. Ready for sp.plan: yes/no

## Response snapshot

Created `specs/002-memory-state/spec.md` covering all 6 scope items as 5 prioritised user stories (P1–P4), 12 functional requirements, 6 key entities, 7 success criteria, 6 assumptions, and an explicit out-of-scope list. No [NEEDS CLARIFICATION] markers — all ambiguities resolved via stated assumptions. Checklist at `specs/002-memory-state/checklists/requirements.md` — all items pass.

## Outcome

- ✅ Impact: Full spec for Phase 2C (memory and state) produced; feature branch 002-memory-state created and checked out
- 🧪 Tests: None (spec phase)
- 📁 Files: specs/002-memory-state/spec.md, specs/002-memory-state/checklists/requirements.md
- 🔁 Next prompts: /sp.plan for 002-memory-state
- 🧠 Reflection: All 6 scope items mapped cleanly to user stories. Cross-channel identity and sentiment trend were the most nuanced; both handled via explicit assumptions rather than clarification questions.

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): checklist — all PASS
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): run /sp.plan to see if FR-005 (sentiment trend) needs further refinement
