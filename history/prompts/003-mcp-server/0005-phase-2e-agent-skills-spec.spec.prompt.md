---
id: "0005"
title: Phase 2E Agent Skills Spec
stage: spec
date: 2026-04-03
surface: agent
model: claude-sonnet-4-6
feature: 003-mcp-server
branch: 003-mcp-server
user: Muhammad Qasim
command: /sp.specify
labels: ["spec", "agent-skills", "phase-2e", "incubation", "skill-manifest"]
links:
  spec: specs/003-mcp-server/spec-2e-agent-skills.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/003-mcp-server/spec-2e-agent-skills.md
  - specs/003-mcp-server/checklists/requirements-2e.md
  - history/prompts/003-mcp-server/0005-phase-2e-agent-skills-spec.spec.prompt.md
tests:
  - null
---

## Prompt

## CONTEXT
Project: CRM Digital FTE Factory — GIAIC Hackathon 5
Location: /home/ps_qasim/projects/crm-digital-fte
Branch: 003-mcp-server (continue on same branch — 2E is part of incubation)
Phase: 2E — Define Agent Skills

All previous phases complete:
- 2B: prototype core loop (79 tests passing)
- 2C: memory & state (ConversationStore, cross-channel identity)
- 2D: MCP server (7 tools, FastMCP, stdio)

Hackathon document: ./The CRM Digital FTE Factory Final Hackathon 5.md
Read Exercise 1.5 section specifically before writing the spec.

## TASK
Run /sp.specify for Phase 2E.

Scope: Define 5 reusable agent skills as formal manifests.
Skills are NOT code — they are structured definitions that describe
WHEN to use a capability, WHAT inputs it takes, WHAT it returns,
and HOW it connects to existing tools/functions.

The 5 required skills (from hackathon Exercise 1.5):

1. Knowledge Retrieval Skill
   - When: customer asks product questions
   - Inputs: query text
   - Outputs: relevant documentation snippets
   - Connects to: search_knowledge_base MCP tool

2. Sentiment Analysis Skill
   - When: every incoming customer message
   - Inputs: message text, conversation history
   - Outputs: sentiment score, trend label, escalation recommendation
   - Connects to: get_sentiment_trend MCP tool + escalation_evaluator.py

3. Escalation Decision Skill
   - When: after generating response
   - Inputs: conversation context, sentiment trend, ticket status
   - Outputs: should_escalate (bool), reason, urgency level
   - Connects to: escalate_to_human MCP tool

4. Channel Adaptation Skill
   - When: before sending ANY response
   - Inputs: response text, target channel
   - Outputs: formatted response appropriate for channel
   - Connects to: channel_formatter.py + send_response MCP tool
   - Rules: email=formal+signature, whatsapp=max 3 sentences, web=semi-formal

5. Customer Identification Skill
   - When: on every incoming message (first step always)
   - Inputs: message metadata (email, phone, channel)
   - Outputs: unified customer_id, merged history, is_returning_customer
   - Connects to: ConversationStore.resolve_identity()

Each skill manifest must define:
- skill_id, name, version
- trigger (when to invoke)
- inputs schema
- outputs schema
- connected_tools (list of MCP tools or functions it calls)
- guardrails (what it must never do)
- test_cases (2-3 example inputs/outputs)

## RULES
- Work in /home/ps_qasim/projects/crm-digital-fte
- Specify only — no code yet
- Commit when done, do NOT push

## WHEN DONE
Confirm: spec file path + 5 skills listed. Ready for sp.plan: yes/no, now i have 2 mcp connect also make remnid it context7 and github check from /mcp now u see also can in update in claude.md? or not

## Response snapshot

Created Phase 2E spec at `specs/003-mcp-server/spec-2e-agent-skills.md` with 5 complete skill manifests:

1. **knowledge_retrieval_v1** — triggers on product questions; connects to `search_knowledge_base` MCP tool; 3 test cases.
2. **sentiment_analysis_v1** — triggers on EVERY inbound message; connects to `get_sentiment_trend` + `ConversationStore.compute_sentiment_trend`; 3 test cases.
3. **escalation_decision_v1** — triggers post-draft; connects to `escalate_to_human` MCP tool + `escalation_evaluator.py`; 3 test cases; references SLA thresholds from `context/escalation-rules.md`.
4. **channel_adaptation_v1** — gates every outbound response; connects to `channel_formatter.py` + `send_response` MCP tool; enforces email=formal+signature, whatsapp=max-3-sentences, web_form=semi-formal; 3 test cases.
5. **customer_identification_v1** — always first (priority 0); connects to `ConversationStore.resolve_identity()`; returns unified customer_id, is_returning_customer, resolution_action; 3 test cases.

Invocation order diagram included. All 12 FRs defined, 7 SCs measurable and technology-agnostic. Checklist at `specs/003-mcp-server/checklists/requirements-2e.md` — all items pass.

## Outcome

- ✅ Impact: Phase 2E spec complete — 5 skill manifests formally defined with I/O schemas, guardrails, and test cases ready for /sp.plan
- 🧪 Tests: 15 skill-level test cases defined (3 per skill) — no code tests yet
- 📁 Files: specs/003-mcp-server/spec-2e-agent-skills.md, specs/003-mcp-server/checklists/requirements-2e.md
- 🔁 Next prompts: /sp.plan for Phase 2E — design skill invocation architecture
- 🧠 Reflection: Skills formalized as YAML manifests within Markdown — machine-parseable and human-readable; invocation order clearly sequenced

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): checklist requirements-2e.md — all items PASS
- Prompt variant (if applicable): null
- Next experiment: verify ConversationStore.resolve_identity() exists before /sp.plan; add if missing
