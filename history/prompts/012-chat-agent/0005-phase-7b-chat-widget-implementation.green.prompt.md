---
id: "0005"
title: "Phase 7B Chat Widget Implementation"
stage: green
date: 2026-04-11
surface: agent
model: claude-sonnet-4-6
feature: 012-chat-agent
branch: 012-chat-agent
user: Muhammad Qasim
command: /sp.implement
labels: ["green", "chat-widget", "fastapi", "openai-agents-sdk", "next.js", "framer-motion", "phase-7b", "rag", "multilingual", "mobile-first"]
links:
  spec: specs/012-chat-agent/spec.md
  ticket: null
  adr: history/adr/0005-chat-endpoint-streaming-vs-non-streaming-design.md
  pr: https://github.com/Psqasim/crm-digital-fte/pull/11
files:
  - production/chat/__init__.py
  - production/chat/session_store.py
  - production/chat/schemas.py
  - production/chat/sanitizer.py
  - production/chat/chat_agent.py
  - production/api/chat_routes.py
  - production/api/main.py
  - src/web-form/hooks/useChatSession.ts
  - src/web-form/components/chat/ChatMessage.tsx
  - src/web-form/components/chat/ChatPanel.tsx
  - src/web-form/components/chat/ChatWidget.tsx
  - src/web-form/components/chat/ChatWidgetPortal.tsx
  - src/web-form/app/api/chat/route.ts
  - src/web-form/app/(main)/layout.tsx
  - tests/test_chat_endpoint.py
  - tests/test_language_detection.py
  - specs/012-chat-agent/tasks.md
tests:
  - tests/test_chat_endpoint.py (8 unit tests — all pass)
  - tests/test_language_detection.py (2 integration tests — skip without API key)
---

## Prompt

## CONTEXT
Project: CRM Digital FTE Factory — GIAIC Hackathon 5
Location: /home/ps_qasim/projects/crm-digital-fte
Branch: 012-chat-agent
Phase: 7B — Chat Agent Widget

Tasks: specs/012-chat-agent/tasks.md (40 tasks T001–T040)
HIGH RISK: T009, T012, T015, T016, T030, T033, T020, T021
Multi-turn pattern: new_input = result.to_input_list() + [{"role":"user","content":msg}]
Current tests: 166 passing

## TASK
Run /sp.implement for all 40 tasks in order T001 → T040.
[... RULES 1-9 as specified, including Context7 mandatory, pytest after HIGH RISK tasks, npm run build, commit + push + PR merge ...]

## Response snapshot

Ran /sp.implement for Phase 7B. All 40 tasks implemented. PR #11 merged to main.

**Context7 confirmed** before any code: `result.to_input_list() + [{"role":"user","content":msg}]`
pattern verified from OpenAI Agents Python docs (Source Reputation: High, 454 snippets).

**Files created** (17 total):
- `production/chat/`: __init__.py, session_store.py, schemas.py, sanitizer.py, chat_agent.py
- `production/api/chat_routes.py` + modified main.py
- `src/web-form/hooks/useChatSession.ts`
- `src/web-form/components/chat/`: ChatMessage, ChatPanel, ChatWidget, ChatWidgetPortal
- `src/web-form/app/api/chat/route.ts` (Next.js proxy to FastAPI)
- `src/web-form/app/(main)/layout.tsx` modified
- `tests/test_chat_endpoint.py`, `tests/test_language_detection.py`

**One bug fixed during implementation**: Test patch path was `production.chat.chat_routes.Runner.run`
(wrong — `chat_routes` is under `production.api`, not `production.chat`). Fixed to
`production.api.chat_routes.Runner.run` → all 8 tests passed.

**One TypeScript fix**: Framer Motion `Variants` type required `type: "spring" as const` — fixed,
build passed.

**pytest**: 174 passed (166 original + 8 new), 0 failures, 2 deselected (integration, no API key).
**npm run build**: ✓ Compiled successfully, 0 errors, 15 routes generated.
**PR**: Psqasim/crm-digital-fte#11 merged to main, branch kept.

## Outcome

- ✅ Impact: Complete Phase 7B — floating AI chat widget end-to-end, RAG-backed, multilingual, mobile-first
- 🧪 Tests: 174 passing (166 + 8 endpoint unit tests); 2 integration tests (skip in CI)
- 📁 Files: 17 files created/modified across backend + frontend + tests + tasks
- 🔁 Next prompts: Phase 7C — Agent Reply Box (if applicable), or HF Spaces deploy
- 🧠 Reflection: Route groups ((main) vs (auth)) handle /login exclusion cleanly — ChatWidgetPortal's usePathname guard is belt-and-suspenders only. The module-level _sessions dict + asyncio single-process model (same as ADR-0001) is correct for HF Spaces. TypeScript `as const` for literal union types in Framer Motion variants is a common gotcha.

## Evaluation notes (flywheel)

- Failure modes observed: (1) Wrong patch path `production.chat.chat_routes` → `production.api.chat_routes` — module structure matters for mocking. (2) Framer Motion `type: "spring"` needs `as const` for TypeScript strict mode.
- Graders run and results (PASS/FAIL): pytest 174/174 PASS; npm build PASS; PR merge PASS
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): Add `pytest-cov` report to verify coverage ≥ 80% on chat module
