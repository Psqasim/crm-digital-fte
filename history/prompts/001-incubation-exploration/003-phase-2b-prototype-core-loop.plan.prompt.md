---
id: 003
title: Phase 2B Prototype Core Loop Plan
stage: plan
date: 2026-04-01
surface: agent
model: claude-sonnet-4-6
feature: 001-incubation-exploration
branch: 001-incubation-exploration
user: Muhammad Qasim
command: /sp.plan
labels: ["plan","phase-2b","prototype","core-loop","escalation","channel-formatting","llm-intent"]
links:
  spec: specs/001-incubation-exploration/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/001-incubation-exploration/plan.md
  - specs/001-incubation-exploration/research.md
  - specs/001-incubation-exploration/data-model.md
  - specs/001-incubation-exploration/quickstart.md
  - specs/001-incubation-exploration/contracts/ticket-input.json
  - specs/001-incubation-exploration/contracts/agent-response.json
  - history/prompts/001-incubation-exploration/003-phase-2b-prototype-core-loop.plan.prompt.md
tests:
  - No code yet — planning only. Tests defined in plan.md T9 acceptance criteria.
---

## Prompt

## CONTEXT
Project: CRM Digital FTE Factory — GIAIC Hackathon 5
Location: /home/ps_qasim/projects/crm-digital-fte
Phase: 2B — Prototype Core Loop
Previous: Phase 2A complete. Discovery log at specs/discovery-log.md.
14 requirements found. Key insight: use LLM-intent detection, not keyword matching.

## TASK
Run /sp.plan for Phase 2B.

The plan must cover building a simple Python prototype that:
1. Takes a customer message as input (with channel metadata: email/whatsapp/web_form)
2. Normalizes the message regardless of source channel
3. Searches product docs for relevant information (simple text search for now)
4. Generates a response using OpenAI API
5. Formats response for the specific channel (email=formal+signature, whatsapp=max 3 sentences, web=semi-formal)
6. Decides if escalation is needed using LLM-intent detection (NOT keyword matching — key lesson from 2A)
7. Injects current datetime using datetime.now(ZoneInfo("Asia/Karachi")) into system prompt

The plan should break this into logical implementation tasks.

## RULES
- Work in /home/ps_qasim/projects/crm-digital-fte
- This is PLANNING only — no code yet
- Output should be the sp.plan artifact saved to specs/

## WHEN DONE
Confirm: plan file path + number of tasks identified. Ready for sp.tasks: yes/no

## Response snapshot

**Plan file**: `specs/001-incubation-exploration/plan.md`
**Tasks identified**: 9 (T1–T9)
**Ready for /sp.tasks**: yes

**Research findings** (research.md — all unknowns resolved):
- Models: gpt-4o-mini for escalation eval (cheap, structured JSON); gpt-4o for response gen (quality)
- Escalation: LLM-intent with JSON output (`{"should_escalate": bool, "reason": str, "urgency": str}`)
- KB search: Jaccard similarity, pure Python sets — no external deps for prototype
- Channel formatting: email=Dear+signature, whatsapp=Hi 👋+≤300 chars, web_form=Hi+semi-formal
- Datetime: `datetime.now(ZoneInfo("Asia/Karachi"))` — stdlib ZoneInfo (Python 3.9+)

**Data model** (data-model.md — 6 entities):
- Channel, TicketMessage, NormalizedTicket, KBResult, EscalationDecision, AgentResponse
- Full data flow diagram + TKT-025 worked example

**Contracts**:
- `contracts/ticket-input.json` — JSON Schema for TicketMessage (oneOf channel validation)
- `contracts/agent-response.json` — JSON Schema for AgentResponse (escalation always set)

**Constitution Check**: All 9 principles PASS. Prototype deviations (no Kafka, in-memory state) explicitly justified per constitution §8 (Incubation Phase Contract).

**Complexity tracking**: 6 prototype simplifications documented with their production replacements.

## Outcome

- ✅ Impact: Plan complete with 9 tasks; all research resolved; data model and contracts written; agent context updated; CLAUDE.md placeholder text fixed
- 🧪 Tests: No tests at plan stage — acceptance criteria defined per task in plan.md
- 📁 Files: specs/001-incubation-exploration/plan.md, research.md, data-model.md, quickstart.md, contracts/ticket-input.json, contracts/agent-response.json
- 🔁 Next prompts: /sp.tasks to generate tasks.md with RED phase test stubs from plan.md tasks
- 🧠 Reflection: Phase 2A false positive analysis (5% FPR from keyword matching) directly drove the most important design decision — LLM-intent for escalation. Research evidence embedded in research.md so the Phase 2B implementor understands WHY, not just what.

## Evaluation notes (flywheel)

- Failure modes observed: update-agent-context.sh ran before plan.md was filled, injecting placeholder text into CLAUDE.md; fixed by editing the Recent Changes section with accurate module descriptions
- Graders run and results (PASS/FAIL): Constitution Check table manually verified — all PASS; plan.md structure matches sp.plan template
- Prompt variant (if applicable): none
- Next experiment: run /sp.tasks immediately — T6 (escalation evaluator) and T8 (core loop) are the highest-risk tasks and should get test stubs first
