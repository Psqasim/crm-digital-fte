---
id: "0001"
title: "Phase 7B Chat Agent Widget Spec"
stage: spec
date: 2026-04-10
surface: agent
model: claude-sonnet-4-6
feature: 012-chat-agent
branch: 012-chat-agent
user: Muhammad Qasim
command: /sp.specify
labels: ["chat-widget", "spec", "phase-7b", "web-chat", "rag", "guardrails", "mobile-responsive"]
links:
  spec: specs/012-chat-agent/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/012-chat-agent/spec.md
  - specs/012-chat-agent/checklists/requirements.md
tests:
  - null
---

## Prompt

## CONTEXT
Project: CRM Digital FTE Factory — GIAIC Hackathon 5
Location: /home/ps_qasim/projects/crm-digital-fte
Phase: 7B — Chat Agent Widget

Frontend: src/web-form/ (Next.js 16.2.2, app router, TypeScript, Tailwind, shadcn/ui, dark theme)
Backend: FastAPI on HF Spaces (https://psqasim-crm-digital-fte-api.hf.space)
Agent: production/agent/customer_success_agent.py (OpenAI Agents SDK, gpt-4o-mini)
Knowledge base: 11 chunks seeded in Neon pgvector

Read before specifying:
- ./The CRM Digital FTE Factory Final Hackathon 5.md
- specs/customer-success-fte-spec.md (§4 agent skills, §8 guardrails)
- production/agent/customer_success_agent.py (process_ticket function)
- context/brand-voice.md (NexaFlow tone)
- .claude/skills/nextjs-16-skill/ (read fully)

## MANDATORY — USE CONTEXT7 BEFORE SPECIFYING
Search:
1. "openai agents sdk streaming response python"
2. "next.js 15 16 server sent events streaming api route"
3. "react chat interface useref scroll bottom"

Do NOT write spec until confirmed.

## TASK
Run /sp.specify for Phase 7B.

## WHAT TO BUILD:
A floating chat widget for NexaFlow — bottom-right corner of every page.
This is a 4th support channel (web_chat) powered by the same OpenAI agent.

Widget UI: floating button (#3B82F6, chat bubble icon), click → slides up panel (Framer Motion),
panel 380px×520px dark #0F172A, header with "NexaFlow AI Support" + minimize + close + clear,
scrollable messages area (auto-scroll to bottom), text input + send button, "Powered by NexaFlow AI" footer.

Chat behavior: greeting on open, history preserved (useState), typing indicator (3 animated dots),
mobile = full screen.

AI behavior: RAG from knowledge_base table (11 chunks), multilingual (auto-detect, respond same language),
CRM purpose only (refusal: "I'm here to help with NexaFlow support only."), NEVER reveal system prompt,
NEVER discuss competitors, rate limit: max 20 msgs/session (warning at 18).

New FastAPI endpoint: POST /chat/message
Request: {message: str, session_id: str, history: [{role, content}]}
Response: {reply: str, session_id: str}
session_id: UUID on first message, last 10 msgs history, no ticket creation, rate limit per session_id.

Security: strip HTML, max 500 chars, refuse prompt injection, rate limit in memory.

Rules: branch 012-chat-agent, specify only, commit when done, do NOT push.

## Response snapshot

Ran /sp.specify for Phase 7B — Chat Agent Widget. Executed:
1. Branch check: no existing 012-chat-agent branches remotely or locally. Highest spec = 011. Confirmed number 012.
2. Read: hackathon docs, customer-success-fte-spec.md §4 & §8 guardrails, customer_success_agent.py (process_ticket architecture), brand-voice.md (NexaFlow tone).
3. Context7 confirmed: OpenAI Agents SDK uses Runner.run_streamed() for streaming; Next.js 16.2.2 supports ReadableStream API in route handlers; React useRef + scrollTop=scrollHeight for auto-scroll.
4. Ran create-new-feature.sh → branch 012-chat-agent created, spec file initialized.
5. Wrote full spec: 5 prioritized user stories, 34 FRs across Widget UI / Chat Behavior / AI Behavior / Rate Limiting / Security / Chat API, 9 measurable technology-agnostic success criteria, 7 assumptions.
6. Created specs/012-chat-agent/checklists/requirements.md — all 13 checklist items pass.
7. Committed both files to 012-chat-agent branch.

## Outcome

- ✅ Impact: Phase 7B spec authored — 5 user stories, 34 FRs, 9 success criteria, all guardrails from §8 encoded, rate limiting and security fully specified, mobile full-screen behavior defined
- 🧪 Tests: null
- 📁 Files: specs/012-chat-agent/spec.md, specs/012-chat-agent/checklists/requirements.md
- 🔁 Next prompts: /sp.plan 012-chat-agent
- 🧠 Reflection: Chat widget is a 4th channel (web_chat) isolated from the Kafka ticket pipeline. Spec correctly scopes it as stateless/self-service with no CRM write-back. Key decision to flag for ADR: streaming vs non-streaming chat endpoint (Runner.run_streamed vs Runner.run).

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): spec quality checklist — all 13 items PASS
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): /sp.plan to determine streaming endpoint architecture
