---
id: "005"
title: Phase 2B Prototype Core Loop Complete
stage: green
date: 2026-04-02
surface: agent
model: claude-sonnet-4-6
feature: 001-incubation-exploration
branch: 001-incubation-exploration
user: Muhammad Qasim
command: /sp.implement
labels: ["implement","prototype","core-loop","tdd","gpt-4o-mini","escalation","knowledge-base"]
links:
  spec: specs/001-incubation-exploration/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - requirements.txt
  - .env.example
  - .gitignore
  - src/__init__.py
  - src/agent/__init__.py
  - src/agent/models.py
  - src/agent/prompts.py
  - src/agent/knowledge_base.py
  - src/agent/channel_formatter.py
  - src/agent/escalation_evaluator.py
  - src/agent/prototype.py
  - tests/__init__.py
  - tests/test_escalation_evaluator.py
  - tests/test_core_loop.py
  - tests/test_prototype.py
  - specs/001-incubation-exploration/tasks.md
tests:
  - tests/test_escalation_evaluator.py (4 tests — escalation TDD)
  - tests/test_core_loop.py (4 tests — core loop TDD)
  - tests/test_prototype.py (8 tests — integration)
---

## Prompt

 ## CONTEXT
Project: CRM Digital FTE Factory — GIAIC Hackathon 5
Location: /home/ps_qasim/projects/crm-digital-fte
Branch: 001-incubation-exploration
Phase: 2B — Prototype Core Loop

Tasks file: specs/001-incubation-exploration/tasks.md
12 tasks (T001–T012). HIGH RISK: T008 (escalation_evaluator), T010 (core loop process_ticket).
Data contracts: specs/001-incubation-exploration/contracts/
Discovery log: specs/discovery-log.md (14 requirements, key insight: LLM-intent for escalation)

## TASK
Run /sp.implement

Implement ALL 12 tasks in order (T001 → T012). Do not skip any.

Key implementation rules:
- T003 prompts.py: System prompt MUST inject datetime.now(ZoneInfo("Asia/Karachi")) 
  at runtime — hardcode nothing
- T008 escalation_evaluator.py: Use LLM-intent detection (ask GPT to classify), 
  NOT keyword matching — this was the key lesson from Phase 2A discovery
- T005 knowledge_base.py: Simple Jaccard/TF-IDF text search against 
  context/product-docs.md — no vector DB yet (that's production Phase 4A)
- T006 channel_formatter.py: Enforce per-channel limits —
  email: full formal response + NexaFlow signature,
  whatsapp: max 3 sentences + no formal greeting,
  web_form: semi-formal + structured next steps
- T010 process_ticket: Must follow this order:
  1. normalize message
  2. search knowledge base
  3. check if escalation needed (T008)
  4. if escalate → return escalation response, skip generation
  5. generate response via OpenAI
  6. format for channel
  7. return AgentResponse dataclass
- T011: CLI runner must test with at least 3 real tickets from 
  context/sample-tickets.json (one per channel)

Use gpt-4o-mini for all OpenAI calls — cost-conscious.

## RULES
- Work in /home/ps_qasim/projects/crm-digital-fte
- Requires OPENAI_API_KEY in environment — create a .env.example showing 
  required vars, but read actual key from .env (do not hardcode)
- After ALL tasks done, run the test suite: pytest tests/ -v
- Commit after implementation: "feat: Phase 2B — prototype core loop complete"
- Do NOT push yet

## Response snapshot

All 12 tasks implemented and committed (b07b964).

**pytest results:** 16/16 passed in 75.72s

**Task status:**
- T001 ✅ requirements.txt + __init__.py files + .env.example
- T002 ✅ models.py — 6 dataclasses (Channel, TicketMessage, NormalizedTicket, KBResult, EscalationDecision, AgentResponse)
- T003 ✅ prompts.py — runtime ZoneInfo("Asia/Karachi") datetime injection
- T004 ✅ prototype.py normalize_message — all 3 channel branches
- T005 ✅ knowledge_base.py — Jaccard search with stop-word filtering + title weighting
- T006 ✅ channel_formatter.py — email/whatsapp/web_form with hard limits
- T007 ✅ test_escalation_evaluator.py — 4 stubs confirmed FAILING before T008
- T008 ✅ escalation_evaluator.py — LLM-intent via gpt-4o-mini JSON mode, no keyword lists
- T009 ✅ test_core_loop.py — 4 stubs confirmed FAILING before T010
- T010 ✅ prototype.py process_ticket — 6-step core loop, short-circuit on escalation
- T011 ✅ CLI runner + test_prototype.py — 8 integration tests
- T012 ✅ quickstart.md validated, CLI runs all 5 tickets cleanly

**CLI sample output (3 channels):**
- TKT-002 (email): Escalated: False | 1882 chars | "Dear James,\n\nTo create an automation..."
- TKT-006 (email): Escalated: True | Urgency: normal | Reason: "Extreme negative emotion and explicit human request"
- TKT-025 (whatsapp): Escalated: False | 206 chars | "Hi Marcus! 👋 It sounds like the Slack notifications..."
- TKT-044 (web_form): Escalated: True | Urgency: normal | Reason: "Legal or compliance concern"

**Issue encountered:** LLM was adding its own greeting before formatter added one, causing double greetings. Fixed by updating system prompt to explicitly tell LLM not to include greeting.

## Outcome

- ✅ Impact: Phase 2B prototype fully operational — 6-step core loop processes all 3 channels, TDD workflow validated for HIGH RISK tasks
- 🧪 Tests: 16/16 passing — 4 escalation unit tests, 4 core loop unit tests, 8 integration tests
- 📁 Files: 16 files created/modified — full agent module at src/agent/
- 🔁 Next prompts: Phase 2C (Memory & State) — persistent ticket store, customer history, pgvector integration
- 🧠 Reflection: LLM-intent escalation with JSON mode + temperature=0 was robust; TKT-003 prorated billing correctly NOT escalated despite "charge" keyword

## Evaluation notes (flywheel)

- Failure modes observed: Double-greeting when LLM adds its own greeting before formatter; fixed by explicit system prompt instruction
- Graders run and results (PASS/FAIL): pytest 16/16 PASS
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): Add pytest marks to skip OpenAI tests when no API key present for CI environments
