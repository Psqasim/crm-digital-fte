---
id: "0001"
title: Phase 2D MCP Server Spec
stage: spec
date: 2026-04-02
surface: agent
model: claude-sonnet-4-6
feature: 003-mcp-server
branch: 003-mcp-server
user: Muhammad Qasim
command: /sp.specify
labels: [mcp, spec, phase-2d, tools, hackathon]
links:
  spec: specs/003-mcp-server/spec.md
  ticket: "null"
  adr: "null"
  pr: "null"
files:
  - specs/003-mcp-server/spec.md
  - specs/003-mcp-server/checklists/requirements.md
tests:
  - "null"
---

## Prompt

 ## CONTEXT
Project: CRM Digital FTE Factory — GIAIC Hackathon 5
Location: /home/ps_qasim/projects/crm-digital-fte
Phase: 2D — Build MCP Server

Previous phases complete:
- 2B: prototype core loop (src/agent/prototype.py, process_ticket, 6-step pipeline)
- 2C: memory & state (src/agent/conversation_store.py, 13 methods, cross-channel identity)
All tests: 52/52 passing

Hackathon document: ./The CRM Digital FTE Factory Final Hackathon 5.md
Constitution: .specify/memory/constitution.md

## TASK
Run /sp.specify for Phase 2D.

Scope: Build an MCP server that exposes the prototype's capabilities as tools.
The hackathon requires MINIMUM 5 tools. We will build 7 to be safe.

Required tools (from hackathon document Exercise 1.4):
1. search_knowledge_base(query) → relevant docs
2. create_ticket(customer_id, issue, priority, channel) → ticket_id
3. get_customer_history(customer_id) → past interactions across ALL channels
4. escalate_to_human(ticket_id, reason) → escalation_id
5. send_response(ticket_id, message, channel) → delivery_status

Two additional tools to add (our enhancements):
6. get_sentiment_trend(customer_id) → trend data + escalation recommendation
7. resolve_ticket(ticket_id, resolution_summary) → confirmation

The MCP server wraps the EXISTING prototype functions — it does not rewrite them.
It calls into: knowledge_base.py, conversation_store.py, escalation_evaluator.py

Use the official MCP Python SDK. Use Context7 to look up current MCP SDK docs.

## RULES
- Work in /home/ps_qasim/projects/crm-digital-fte
- New branch: 003-mcp-server
- Specify only — no code yet
- Commit when done, do NOT push

## WHEN DONE
Confirm: spec file path + 7 tools listed with their signatures.
Ready for sp.plan: yes/no

## Response snapshot

Created branch `003-mcp-server` (number 003, no prior mcp-server branches/specs found). Wrote spec at `specs/003-mcp-server/spec.md` with 7 user stories (one per tool), 13 functional requirements, 7 success criteria, key entities, assumptions, out-of-scope, and dependencies. Checklist at `specs/003-mcp-server/checklists/requirements.md` — all 14 items pass. Committed as `spec: Phase 2D — MCP server tool gateway specification`.

## Outcome

- ✅ Impact: Phase 2D spec complete; 7 tools fully specified with signatures, acceptance scenarios, and measurable success criteria.
- 🧪 Tests: No code tests (spec-only phase); checklist validation passed (14/14).
- 📁 Files: specs/003-mcp-server/spec.md, specs/003-mcp-server/checklists/requirements.md
- 🔁 Next prompts: /sp.plan for Phase 2D architecture and implementation design
- 🧠 Reflection: Spec cleanly separates what/why from how; all 7 tools have clear business-level acceptance scenarios without leaking MCP SDK details.

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): spec checklist 14/14 PASS
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): N/A
