# Implementation Plan: Phase 2E — Agent Skills Definition + Wiring

**Branch**: `003-mcp-server` | **Date**: 2026-04-03 | **Spec**: `specs/003-mcp-server/spec-2e-agent-skills.md`

---

## Summary

Define 5 agent skill manifests as Python dataclasses (`skills_manifest.py`), build a static registry (`skills_registry.py`), and wire an invoker (`skills_invoker.py`) that orchestrates all 5 skills in priority order 0→4 for every incoming message. Update `prototype.py::process_ticket` to delegate to the invoker instead of calling `conversation_store`, `escalation_evaluator`, `channel_formatter`, and `knowledge_base` directly.

**No new business logic. No new dependencies. No new MCP tools. Pure wiring.**

---

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: None new — `dataclasses` (stdlib), existing agent modules
**Storage**: N/A — in-memory only; no new persistence
**Testing**: `pytest` — unit tests for registry + invoker orchestration order
**Target Platform**: Same Linux/WSL2 dev environment; importable as `src.agent.*`
**Performance Goals**: No measurable overhead — all new code is thin wrappers over existing calls
**Constraints**: Must not break any of the 79 existing passing tests
**Scale/Scope**: 5 skill manifests, 3 new Python modules, 1 modified module (`prototype.py`)

---

## Constitution Check

**Gate check — all must pass before implementation:**

| Gate | Status | Notes |
|------|--------|-------|
| Datetime injection in agent system prompt | PASS — unchanged | `prompts.py` already injects PKT datetime |
| `create_ticket` called before LLM response | PASS — unchanged | `process_ticket` flow preserved |
| Customer identity unified by email/phone | PASS — invoker wraps `resolve_identity()` | No change to the logic |
| Channel-adaptive responses | PASS — `channel_adaptation_v1` gates every outbound | `channel_formatter.py` unchanged |
| Sentiment analyzed before ticket close | PASS — `sentiment_analysis_v1` runs on every message | `compute_sentiment_trend()` unchanged |
| Escalation triggers all 8 conditions | PASS — `escalation_decision_v1` wraps `evaluate_escalation()` | No trigger logic changed |
| No new external dependencies | PASS — `dataclasses` is stdlib | |
| Smallest viable change | PASS — wiring only; no business logic added | |

**Constitution violation**: None. No Complexity Tracking entry needed.

---

## Project Structure

### Documentation (Phase 2E)

```text
specs/003-mcp-server/
├── spec-2e-agent-skills.md      # Phase 2E spec (done)
├── plan-2e-agent-skills.md      # This file
├── research-2e.md               # Wiring decisions (done)
├── data-model-2e.md             # Dataclass schemas (done)
├── contracts/
│   └── skills_invoker_contract.py   # Typed interface contract (done)
└── checklists/
    └── requirements-2e.md       # Spec checklist (done)
```

### Source Code (new files)

```text
src/agent/
├── skills_manifest.py   ← NEW: 5 SkillManifest dataclass instances
├── skills_registry.py   ← NEW: dict[str, SkillManifest] + get_skill() / list_skills()
├── skills_invoker.py    ← NEW: SkillsInvoker.run() + apply_channel_adaptation()
└── prototype.py         ← MODIFIED: process_ticket delegates to SkillsInvoker

tests/
└── test_skills.py       ← NEW: registry lookup + invoker orchestration tests
```

---

## Phase 0: Research

**Status**: Complete. See `research-2e.md`.

Key findings:
- `ConversationStore.resolve_identity()` exists at `conversation_store.py:114` — used by Customer Identification Skill.
- `compute_sentiment_trend()` exists at `conversation_store.py:268` — used by Sentiment Analysis Skill.
- `KnowledgeBase.search()` exists at `knowledge_base.py:66` — used by Knowledge Retrieval Skill.
- `evaluate_escalation()` exists at `escalation_evaluator.py:64` — used by Escalation Decision Skill.
- `format_response()` exists at `channel_formatter.py:17` — used by Channel Adaptation Skill.
- No new packages required. No NEEDS CLARIFICATION items remain.

---

## Phase 1: Design + Contracts

### 1A — Data Model

**See `data-model-2e.md` for full schema.**

Summary:

```python
# skills_manifest.py
@dataclass(frozen=True)
class SkillManifest:
    skill_id: str
    name: str
    version: str
    priority: int          # 0 = first, 4 = last
    trigger: str
    connected_tools: list[str]
    guardrails: list[str]

CUSTOMER_IDENTIFICATION = SkillManifest(skill_id="customer_identification_v1", priority=0, ...)
SENTIMENT_ANALYSIS      = SkillManifest(skill_id="sentiment_analysis_v1",      priority=1, ...)
KNOWLEDGE_RETRIEVAL     = SkillManifest(skill_id="knowledge_retrieval_v1",      priority=2, ...)
ESCALATION_DECISION     = SkillManifest(skill_id="escalation_decision_v1",      priority=3, ...)
CHANNEL_ADAPTATION      = SkillManifest(skill_id="channel_adaptation_v1",       priority=4, ...)

SKILLS: list[SkillManifest] = [
    CUSTOMER_IDENTIFICATION, SENTIMENT_ANALYSIS, KNOWLEDGE_RETRIEVAL,
    ESCALATION_DECISION, CHANNEL_ADAPTATION,
]
```

```python
# skills_invoker.py — per-skill result types
@dataclass class CustomerIdentificationResult: customer_id, is_returning_customer, customer_plan, resolution_action
@dataclass class SentimentAnalysisResult: sentiment_score, sentiment_label, trend_label, escalation_recommended, data_points_used
@dataclass class KnowledgeRetrievalResult: results, result_count
@dataclass class EscalationDecisionResult: should_escalate, reason, urgency
@dataclass class ChannelAdaptationResult: formatted_response, channel_applied, formatting_notes
@dataclass class InvokerResult: customer_id_result, sentiment_result, kb_result, escalation_result, channel_result
```

### 1B — API Contracts

**See `contracts/skills_invoker_contract.py` for full typed interface.**

Key interface:

```python
class SkillsInvoker:
    def run(self, msg: TicketMessage) -> InvokerResult:
        # Executes skills 0–3; channel_result is None on return
        ...

    def apply_channel_adaptation(
        self, result: InvokerResult, raw_response: str,
        channel: str, customer_name: str
    ) -> InvokerResult:
        # Executes skill 4 after LLM draft is available
        # Raises ValueError if should_escalate is True
        ...
```

```python
class SkillsRegistry:
    def get_skill(self, skill_id: str) -> SkillManifest:  # raises KeyError if not found
    def list_skills(self) -> list[SkillManifest]:          # sorted by priority ascending
```

### 1C — Invocation Wiring (skills_invoker.py internals)

```
SkillsInvoker.run(msg):
  1. _run_customer_identification(msg)
       → store.resolve_identity(email, phone)
       → store.get_or_create_customer(key, name, channel)
       → return CustomerIdentificationResult

  2. _run_sentiment_analysis(msg, customer_id_result)
       → store.get_or_create_conversation(customer_key, channel)
       → store.compute_sentiment_trend(conversation)
       → map SentimentTrend → SentimentAnalysisResult

  3. _run_knowledge_retrieval(msg)  [CONDITIONAL: if message is product question]
       → _kb.search(topic + message[:200], top_k=3)
       → return KnowledgeRetrievalResult (or KnowledgeRetrievalResult(results=[], result_count=0))

  4. _run_escalation_decision(msg, sentiment_result)
       → evaluate_escalation(message)
       → supplement with sentiment_result.escalation_recommended
       → return EscalationDecisionResult

  return InvokerResult(customer_id_result, sentiment_result, kb_result, escalation_result, channel_result=None)
```

```
SkillsInvoker.apply_channel_adaptation(result, raw_response, channel, customer_name):
  → format_response(raw_response, channel, customer_name)
  → build ChannelAdaptationResult with formatting_notes
  → return InvokerResult with channel_result populated
```

### 1D — process_ticket Wiring (prototype.py changes)

**Before (current):**
```python
customer_key = store.resolve_identity(email, phone)
store.get_or_create_customer(...)
conversation = store.get_or_create_conversation(...)
conversation_context = store.get_conversation_context(customer_key)
kb_results = _kb.search(topic + message[:200])
escalation = evaluate_escalation(ticket.message)
# ... escalation check ...
formatted = format_response(raw, ticket.channel, ticket.customer_first_name)
```

**After (Phase 2E):**
```python
invoker = SkillsInvoker()
result = invoker.run(msg)
customer_key = result.customer_id_result.customer_id
conversation = store.get_or_create_conversation(customer_key, ticket.channel.value)
conversation_context = store.get_conversation_context(customer_key)
kb_results = result.kb_result.results if result.kb_result else []
escalation = _map_escalation_result(result.escalation_result)  # thin adapter
# ... escalation check (unchanged logic) ...
result = invoker.apply_channel_adaptation(result, raw, ticket.channel.value, ticket.customer_first_name)
formatted = result.channel_result.formatted_response
```

**`AgentResponse` output contract is unchanged.**

### 1E — quickstart.md

See `quickstart-2e.md` (generated below).

---

## Implementation Tasks

These tasks are for `/sp.tasks` to expand into full testable task definitions.

| # | Task | Files | Est. |
|---|------|-------|------|
| T01 | Create `skills_manifest.py` with `SkillManifest` dataclass + 5 constants | `src/agent/skills_manifest.py` | Small |
| T02 | Create `skills_registry.py` with `SkillsRegistry` class | `src/agent/skills_registry.py` | Small |
| T03 | Create `skills_invoker.py` — result dataclasses | `src/agent/skills_invoker.py` | Small |
| T04 | Implement `SkillsInvoker._run_customer_identification()` | `src/agent/skills_invoker.py` | Small |
| T05 | Implement `SkillsInvoker._run_sentiment_analysis()` | `src/agent/skills_invoker.py` | Small |
| T06 | Implement `SkillsInvoker._run_knowledge_retrieval()` (conditional) | `src/agent/skills_invoker.py` | Small |
| T07 | Implement `SkillsInvoker._run_escalation_decision()` | `src/agent/skills_invoker.py` | Small |
| T08 | Implement `SkillsInvoker.run()` and `apply_channel_adaptation()` | `src/agent/skills_invoker.py` | Small |
| T09 | Update `prototype.py::process_ticket` to use `SkillsInvoker` | `src/agent/prototype.py` | Medium |
| T10 | Write `tests/test_skills.py` — registry lookup + invoker order tests | `tests/test_skills.py` | Medium |

**Total tasks: 10**

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Regression in 79 existing tests | Low | High | Run full test suite after each task; T09 is gated on T01–T08 passing |
| `SentimentTrend` → `SentimentAnalysisResult` mapping mismatch | Medium | Low | Thin adapter function; covered by T10 test cases |
| `process_ticket` diff introduces subtle ordering bug | Low | High | T10 includes an end-to-end invocation order assertion |

---

## ADR Note

📋 Architectural decision detected: **Sequential synchronous skill pipeline vs. async/event-driven** — current design locks to sync; async is needed for Phase 3 Kafka integration.
Document reasoning and tradeoffs? Run `/sp.adr skill-pipeline-sync-vs-async`
