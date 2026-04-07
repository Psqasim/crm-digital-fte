---
id: "0001"
title: Phase 4B Production Agent Spec
stage: spec
date: 2026-04-04
surface: agent
model: claude-sonnet-4-6
feature: 006-production-agent
branch: 006-production-agent
user: Muhammad Qasim
command: /sp.specify
labels: ["spec","openai-agents-sdk","production-agent","function-tool","phase-4b"]
links:
  spec: specs/006-production-agent/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/006-production-agent/spec.md
  - specs/006-production-agent/checklists/requirements.md
  - history/prompts/006-production-agent/0001-phase-4b-production-agent-spec.spec.prompt.md
tests:
  - null
---

## Prompt

## CONTEXT
Project: CRM Digital FTE Factory — GIAIC Hackathon 5
Location: /home/ps_qasim/projects/crm-digital-fte
Phase: 4B — OpenAI Agents SDK Agent Implementation

Phase 4A complete: 8-table PostgreSQL schema, 13 async query functions,
injectable pool pattern (ADR-0001). Branch 005-production-db merged to main.

Files to read before specifying:
- ./The CRM Digital FTE Factory Final Hackathon 5.md 
  (Transition Step 3 — "Transform MCP Tools to Production Tools" section)
- specs/customer-success-fte-spec.md (§4 Agent Skills, §5 MCP Tools, §8 Guardrails)
- production/database/queries.py (13 functions the agent will call)
- src/agent/prompts.py (working system prompt from prototype — port this)
- .specify/memory/constitution.md (§4 Agent Behavioral Contract)

## MANDATORY — USE CONTEXT7 BEFORE SPECIFYING
This is a complex pillar. Use Context7 MCP right now, search:
1. "openai agents sdk python agent function_tool" — current Agent class API
2. "openai agents sdk runner run_sync async" — how to run agent
3. "openai agents sdk function_tool pydantic input" — tool input schemas

Do NOT write the spec until Context7 results confirmed.

## TASK
Run /sp.specify for Phase 4B.

Scope — implement production/agent/customer_success_agent.py and supporting files:

**The agent must have these @function_tool decorated tools (7 total):**
1. search_knowledge_base — vector search via queries.py, pgvector
2. create_ticket — via queries.py, returns ticket_id
3. get_customer_history — via queries.py, all channels
4. escalate_to_human — updates ticket status, returns escalation_id
5. send_response — routes to correct channel handler (stub for now — 
   channels implemented in 4C, but tool signature defined here)
6. get_sentiment_trend — via queries.py
7. resolve_ticket — updates ticket status to resolved

**The system prompt must:**
- Inject datetime.now(ZoneInfo("Asia/Karachi")) at runtime (Rule 10 — non-negotiable)
- Include NexaFlow company context
- Include all ALWAYS/NEVER guardrails from constitution §4
- Be channel-aware (different tone instruction per channel passed in)
- Reference spec §8 guardrails exactly

**The agent must:**
- Use gpt-4o-mini (cost-conscious)
- Accept channel as input parameter
- Return structured AgentResponse (same contract as prototype)
- Handle OpenAI API errors gracefully (retry once, then escalate)

**production/agent/formatters.py:**
Port channel_formatter.py from prototype — same logic, production structure

**production/agent/prompts.py:**
Port prompts.py from prototype — add channel-aware sections

## RULES
- Work in /home/ps_qasim/projects/crm-digital-fte
- New branch: 006-production-agent
- Specify only — no code yet
- Commit when done, do NOT push

## WHEN DONE
Confirm: spec file path + 7 tools listed + Context7 findings noted.
Ready for sp.plan: yes/no

## Response snapshot

Context7 confirmed (`/openai/openai-agents-python`, benchmark 85.31):
- `@function_tool` auto-extracts name/description/schema from type hints + docstring; supports async and sync functions; TypedDict and Pydantic `BaseModel` supported for structured inputs; `Annotated[T, Field(...)]` for parameter constraints
- `Agent(name=..., instructions=..., tools=[...])` constructor; `model=` parameter sets inference model
- `Runner.run()` — async, returns `RunResult`; `Runner.run_sync()` — synchronous wrapper; `Runner.run_streamed()` — async streaming

Spec written with:
- 3 user stories (P1: new customer, P2: returning cross-channel, P3: escalation)
- 8 edge cases documented
- FR-001 – FR-042: 42 functional requirements covering agent core, 7 tools, system prompt, formatters
- Guardrails section with all 7 ALWAYS + 8 NEVER rules embedded verbatim from Constitution §IV
- 3 key entities: AgentResponse, FormattedResponse, CustomerContext
- 8 success criteria (SC-001 – SC-008)
- All checklist items passed

## Outcome

- ✅ Impact: Complete Phase 4B spec covering production agent, 7 function_tools, prompts.py, and formatters.py
- 🧪 Tests: No tests run (spec phase)
- 📁 Files: specs/006-production-agent/spec.md, specs/006-production-agent/checklists/requirements.md
- 🔁 Next prompts: /sp.plan for Phase 4B
- 🧠 Reflection: Context7 confirmed @function_tool API before writing — tool call ordering and channel-aware prompt design are the highest-risk implementation decisions for /sp.plan

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): requirements checklist — PASS (all 14 items)
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): Run /sp.plan to validate tool input schema design choices
