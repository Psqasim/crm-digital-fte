---
id: "0003"
title: "Phase 7B Chat Widget Implementation Plan"
stage: plan
date: 2026-04-10
surface: agent
model: claude-sonnet-4-6
feature: 012-chat-agent
branch: 012-chat-agent
user: Muhammad Qasim
command: /sp.plan
labels: ["plan", "chat-widget", "fastapi", "openai-agents-sdk", "next.js", "framer-motion", "phase-7b"]
links:
  spec: specs/012-chat-agent/spec.md
  ticket: null
  adr: history/adr/0005-chat-endpoint-streaming-vs-non-streaming-design.md
  pr: null
files:
  - specs/012-chat-agent/plan.md
  - specs/012-chat-agent/research.md
  - specs/012-chat-agent/data-model.md
  - specs/012-chat-agent/quickstart.md
  - specs/012-chat-agent/contracts/chat-endpoint.yaml
  - CLAUDE.md
tests:
  - null
---

## Prompt

## CONTEXT
Project: CRM Digital FTE Factory — GIAIC Hackathon 5
Location: /home/ps_qasim/projects/crm-digital-fte
Branch: 012-chat-agent
Phase: 7B — Chat Agent Widget

Spec: specs/012-chat-agent/spec.md (34 FRs, 5 user stories)
Chat is isolated from ticket pipeline — no Kafka, no ticket creation.

## TASK
Run /sp.plan with constraints:
- OpenAI Agents SDK (Agent + Runner.run(), not raw API)
- Multi-turn history via input_items list (Context7 confirm before planning)
- Clear chat: frontend clears state + new session_id
- Block 1: FastAPI chat endpoint (session store, agent, sanitizer, rate limiting, language detection)
- Block 2: Next.js chat widget (ChatWidget, ChatPanel, ChatMessage, useChatSession)
- Block 3: Layout integration (root layout, hide on /login)
- Block 4: Tests (endpoint unit tests, language detection)

## Response snapshot

Ran /sp.plan for Phase 7B. All Phase 0 + Phase 1 artifacts created.

**Context7 confirmed**: Multi-turn history uses `result.to_input_list() + [{"role": "user", "content": msg}]`
pattern. Server stores accumulated input_items per session, trimmed to last 20 items (10 turns).
SQLiteSession rejected — ephemeral in-memory store is sufficient.

**7 research items resolved** (R-001 to R-007): multi-turn pattern, injection blocklist (9 patterns),
language detection via system prompt instruction, session store design, Framer Motion animations,
CORS (no changes), layout insertion via ChatWidgetPortal client wrapper.

**Plan: 12 tasks across 4 blocks**:
- Block 1 (B1-T1..T4): ChatSession store + schemas, sanitizer, chat agent (2 tools), chat router
- Block 2 (B2-T1..T4): useChatSession hook, ChatMessage, ChatPanel, ChatWidget (floating + animated)
- Block 3 (B3-T1..T2): ChatWidgetPortal (usePathname, skip /login), root layout.tsx modification
- Block 4 (B4-T1..T2): 8 endpoint unit tests, 2 language detection integration tests

**HIGH RISK tasks**: B1-T4 (Router — input_items format), B1-T3 (Chat agent system prompt effectiveness), B2-T1 (useChatSession session lifecycle edge cases)

Constitution exception: Kafka bypass justified (chat = stateless self-service, no ticket creation).

## Outcome

- ✅ Impact: Complete implementation plan ready — 12 tasks, 5 new files in plan artifacts, 9 new source files identified, 2 test files planned
- 🧪 Tests: tests/test_chat_endpoint.py (8 unit tests), tests/test_language_detection.py (2 integration tests)
- 📁 Files: specs/012-chat-agent/plan.md, research.md, data-model.md, quickstart.md, contracts/chat-endpoint.yaml, CLAUDE.md (context updated)
- 🔁 Next prompts: /sp.tasks 012-chat-agent
- 🧠 Reflection: Manual input_items approach gives explicit 10-turn window control vs SQLiteSession auto-management. ChatWidgetPortal as thin client wrapper for login exclusion is the cleanest Next.js 16 pattern for conditional rendering in Server Component layouts.

## Evaluation notes (flywheel)

- Failure modes observed: setup-plan.sh complained about missing plan.md initially (expected — it creates it). No blockers.
- Graders run and results (PASS/FAIL): Constitution check — 5 PASS, 1 JUSTIFIED exception (Kafka bypass)
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): /sp.tasks to break plan blocks into atomic implementation tasks
