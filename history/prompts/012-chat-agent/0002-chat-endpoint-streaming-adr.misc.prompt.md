---
id: "0002"
title: "Chat Endpoint Streaming ADR"
stage: misc
date: 2026-04-10
surface: agent
model: claude-sonnet-4-6
feature: 012-chat-agent
branch: 012-chat-agent
user: Muhammad Qasim
command: /sp.adr
labels: ["adr", "streaming", "sse", "chat-endpoint", "phase-7b", "architecture"]
links:
  spec: specs/012-chat-agent/spec.md
  ticket: null
  adr: history/adr/0005-chat-endpoint-streaming-vs-non-streaming-design.md
  pr: null
files:
  - history/adr/0005-chat-endpoint-streaming-vs-non-streaming-design.md
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
/sp.adr streaming-chat-endpoint
Document: streaming (SSE + Runner.run_streamed) vs non-streaming (Runner.run + JSON).
Decision must consider: frontend complexity, perceived UX, token limits,
OpenAI Agents SDK support. Pick one and justify.

## RULES
- Work in /home/ps_qasim/projects/crm-digital-fte
- Commit, do NOT push

## Response snapshot

Created ADR-0005: Chat Endpoint — Streaming vs Non-Streaming Response Design.

Decision: **Non-streaming JSON (Runner.run + POST → {reply, session_id})** accepted for Phase 7B.

Key analysis: gpt-4o-mini responses are 50–200 tokens at ~50-80 tok/s (1–4s total). Typing indicator
adequately masks this wait; streaming UX advantage is marginal at this response scale. HF Spaces SSE
long-lived connection reliability is not documented for the free tier. Streaming requires ~3× more
frontend code (partial-message state, error handling, reconnection). Both SSE and WebSocket alternatives
documented and rejected with rationale. Upgrade path to Phase 8 streaming preserved.

Significance test: all 3 criteria pass (Impact + Alternatives + Cross-cutting scope).
Existing ADRs 0001–0004: no conflicts detected.

## Outcome

- ✅ Impact: ADR-0005 accepted — non-streaming JSON design chosen for Phase 7B chat endpoint; streaming explicitly deferred to Phase 8 with documented upgrade path
- 🧪 Tests: null
- 📁 Files: history/adr/0005-chat-endpoint-streaming-vs-non-streaming-design.md
- 🔁 Next prompts: /sp.plan 012-chat-agent
- 🧠 Reflection: Architectural decision was identifiable from spec-phase Context7 research (Runner.run_streamed vs Runner.run) without requiring plan.md. ADR created pre-plan is appropriate when the choice directly constrains implementation approach.

## Evaluation notes (flywheel)

- Failure modes observed: check-prerequisites.sh requires plan.md and aborted — ADR created directly per user instruction. Prerequisite check is advisory for ADR creation, not mandatory.
- Graders run and results (PASS/FAIL): Significance checklist — all 3 criteria PASS
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): /sp.plan to verify non-streaming design integrates cleanly with widget architecture
