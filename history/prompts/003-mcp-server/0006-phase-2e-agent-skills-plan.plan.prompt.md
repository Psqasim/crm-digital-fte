---
id: "0006"
title: Phase 2E Agent Skills Plan
stage: plan
date: 2026-04-03
surface: agent
model: claude-sonnet-4-6
feature: 003-mcp-server
branch: 003-mcp-server
user: Muhammad Qasim
command: /sp.plan
labels: ["plan", "agent-skills", "phase-2e", "skills-invoker", "wiring"]
links:
  spec: specs/003-mcp-server/spec-2e-agent-skills.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/003-mcp-server/plan-2e-agent-skills.md
  - specs/003-mcp-server/research-2e.md
  - specs/003-mcp-server/data-model-2e.md
  - specs/003-mcp-server/quickstart-2e.md
  - specs/003-mcp-server/contracts/skills_invoker_contract.py
tests:
  - null
---

## Prompt

## CONTEXT
Project: CRM Digital FTE Factory — GIAIC Hackathon 5
Location: /home/ps_qasim/projects/crm-digital-fte
Branch: 003-mcp-server
Phase: 2E — Agent Skills

Spec: specs/003-mcp-server/spec-2e-agent-skills.md
5 skills defined with invocation order:
0: customer_identification_v1 (always first)
1: sentiment_analysis_v1
2: knowledge_retrieval_v1
3: escalation_decision_v1
4: channel_adaptation_v1

## TASK
Run /sp.plan for Phase 2E.

Plan must cover:
- Skills manifest file: src/agent/skills_manifest.py
  (Python dataclasses or TypedDict representing each skill definition)
- Skills registry: src/agent/skills_registry.py
  (loads all 5 skills, provides get_skill(skill_id) lookup)
- Skills invoker: src/agent/skills_invoker.py
  (orchestrates the 5 skills in priority order 0→4 for each incoming message)
- Update prototype.py process_ticket to use skills_invoker instead of
  calling components directly
- Tests for registry lookup and invoker orchestration order

This phase is definition + wiring — skills call the EXISTING functions
(conversation_store, escalation_evaluator, channel_formatter, knowledge_base,
MCP tools). No new business logic.

## RULES
- Work in /home/ps_qasim/projects/crm-digital-fte
- Planning only — no code yet
- Commit when done, do NOT push

## WHEN DONE
Confirm: plan file path + task count. Ready for sp.tasks: yes/no

## Response snapshot

Created Phase 2E plan at `specs/003-mcp-server/plan-2e-agent-skills.md` with 10 implementation tasks.

**Architecture decisions:**
- `SkillManifest`: frozen `@dataclass` (consistent with existing codebase; 5 module-level constants + `SKILLS` list)
- `SkillsRegistry`: module-level dict, `get_skill(skill_id)` raises KeyError on miss, `list_skills()` sorted by priority
- `SkillsInvoker.run(msg)`: sequential pipeline 0→3; returns `InvokerResult` with `channel_result=None`
- `SkillsInvoker.apply_channel_adaptation(result, raw, channel, name)`: skill 4 called post-LLM-draft
- `process_ticket` change: wraps existing calls behind invoker; `AgentResponse` output contract unchanged

**10 tasks defined:** T01 manifest, T02 registry, T03 result dataclasses, T04–T08 invoker methods, T09 prototype wiring, T10 tests.

**Constitution gates**: all pass — no new dependencies, no new business logic, smallest viable change.

**ADR suggestion**: 📋 skill-pipeline-sync-vs-async — sequential sync design noted; async needed for Kafka (Phase 3).

## Outcome

- ✅ Impact: Phase 2E plan complete — 10 tasks, 3 new modules, 1 modified; all wiring decisions documented
- 🧪 Tests: tests/test_skills.py defined in plan (registry lookup + invoker order assertions)
- 📁 Files: plan-2e-agent-skills.md, research-2e.md, data-model-2e.md, quickstart-2e.md, contracts/skills_invoker_contract.py
- 🔁 Next prompts: /sp.tasks for Phase 2E
- 🧠 Reflection: All 5 target functions exist and are tested — this is pure wiring with minimal risk

## Evaluation notes (flywheel)

- Failure modes observed: setup-plan.sh overwrote plan.md; restored from git before writing 2E plan
- Graders run and results (PASS/FAIL): constitution check — all 8 gates PASS
- Prompt variant (if applicable): null
- Next experiment: null
