---
id: "0002"
title: Tool Input Schema ADR
stage: misc
date: 2026-04-04
surface: agent
model: claude-sonnet-4-6
feature: 006-production-agent
branch: 006-production-agent
user: Muhammad Qasim
command: /sp.adr
labels: ["adr","pydantic","typeddict","function-tool","openai-agents-sdk","phase-4b"]
links:
  spec: specs/006-production-agent/spec.md
  ticket: null
  adr: history/adr/0003-tool-input-schema-design-pydantic-basemodel-vs-typeddict.md
  pr: null
files:
  - history/adr/0003-tool-input-schema-design-pydantic-basemodel-vs-typeddict.md
  - history/prompts/006-production-agent/0002-tool-input-schema-adr.misc.prompt.md
tests:
  - null
---

## Prompt

## CONTEXT
Project: CRM Digital FTE Factory — GIAIC Hackathon 5
Location: /home/ps_qasim/projects/crm-digital-fte
Branch: 006-production-agent
Phase: 4B — OpenAI Agents SDK Agent

Spec: specs/006-production-agent/spec.md (14/14 checklist pass)
7 tools confirmed. Context7 verified: @function_tool, Runner.run(), 
Pydantic BaseModel inputs, Annotated[T, Field()] constraints.
DB queries ready in production/database/queries.py (13 async functions)
Prototype prompts: src/agent/prompts.py (port to production)

## TASK
Do things in order:

### Part A — ADR first
/sp.adr tool-input-schema-design
Document: Pydantic BaseModel vs TypedDict for @function_tool inputs.
Include: validation depth, testability, OpenAI SDK compatibility,
and which we chose and why.

## RULES
- Work in /home/ps_qasim/projects/crm-digital-fte
- Commit , do NOT push

## WHEN DONE
Confirm: ADR path

## Response snapshot

Created ADR-0003: Tool Input Schema Design — Pydantic BaseModel vs TypedDict.

**Decision:** Pydantic BaseModel for tools with 3+ parameters or validation constraints; Annotated[T, Field()] primitives for 1–2 parameter tools.

Tool mapping:
- search_knowledge_base → SearchKBInput BaseModel (query max_length + limit range)
- create_ticket → CreateTicketInput BaseModel (5 params, channel enum)
- get_customer_history → Annotated primitives (2 params, no constraints)
- escalate_to_human → EscalateInput BaseModel (urgency enum + non-empty reason)
- send_response → SendResponseInput BaseModel (channel enum + non-empty message)
- get_sentiment_trend → Annotated primitives (2 params, no constraints)
- resolve_ticket → ResolveTicketInput BaseModel (non-empty resolution_summary)

**Alternatives rejected:** TypedDict (no runtime validation, weak JSON Schema), plain positional params (no Field descriptions for LLM), dict (fully untyped).

No conflicts with ADR-0001 or ADR-0002.

## Outcome

- ✅ Impact: ADR-0003 documents the cross-cutting tool input schema pattern for all 7 Phase 4B tools
- 🧪 Tests: No tests run (ADR documentation phase)
- 📁 Files: history/adr/0003-tool-input-schema-design-pydantic-basemodel-vs-typeddict.md
- 🔁 Next prompts: /sp.plan for Phase 4B
- 🧠 Reflection: Mixed BaseModel + Annotated approach avoids boilerplate for simple tools while retaining validation at tool boundaries where it matters most

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): significance checklist — PASS (cross-cutting, 3 alternatives, long-term impact)
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): Verify BaseModel JSON Schema output via @function_tool introspection in Phase 4B implementation
