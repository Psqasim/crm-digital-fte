# Research: Phase 2E — Agent Skills Wiring

**Date**: 2026-04-03
**Branch**: `003-mcp-server`
**Phase**: 2E — Define + Wire Agent Skills

---

## Purpose

No external unknowns in Phase 2E. All modules exist and are tested. This document maps each skill to its concrete implementation anchor in the current codebase and records the key wiring decisions.

---

## Decision 1: Skill Manifest Representation

**Decision**: Python `@dataclass` for `SkillManifest`, not `TypedDict`.

**Rationale**: The existing codebase uses `@dataclass` throughout (`models.py`, `conversation_store.py`). Dataclasses provide default values, `__repr__`, and are easier to extend with methods. TypedDict adds no benefit when the structures are created once at module load time, not deserialized from JSON.

**Alternatives considered**:
- `TypedDict` — too flat; no default values without `total=False` workarounds.
- Pydantic `BaseModel` — over-engineered for static in-memory manifest definitions; adds a dependency that isn't needed until the HTTP layer.

---

## Decision 2: Skills Registry Strategy

**Decision**: Module-level `dict[str, SkillManifest]` built from a `SKILLS` list constant, accessed via `get_skill(skill_id: str) → SkillManifest`.

**Rationale**: The 5 skills are static — they are defined at author time, not at runtime. A simple dict is O(1) lookup with zero dependencies. No dynamic loading, no YAML parsing, no file I/O.

**Alternatives considered**:
- YAML/JSON file loaded at runtime — adds I/O, serialization, and path resolution complexity for no benefit in Phase 2E.
- Class-based registry with `register()` decorator — unnecessary abstraction for 5 fixed entries.

---

## Decision 3: Skills Invoker Architecture

**Decision**: `SkillsInvoker.run(msg: TicketMessage) → InvokerResult` — a sequential pipeline that calls each skill adapter in priority order (0→4) and accumulates results into a structured `InvokerResult` dataclass.

**Rationale**:
- Each skill becomes a thin adapter method (`_run_customer_id`, `_run_sentiment`, etc.) that wraps an existing function. No new business logic — just routing and result collection.
- `InvokerResult` carries the outputs of all 5 skills so `process_ticket` can access them without re-querying any module.
- Early-exit on escalation: if Escalation Decision returns `should_escalate=True`, the invoker sets a flag and `process_ticket` skips LLM generation.

**Alternatives considered**:
- Async pipeline — unnecessary until Kafka integration (Phase 3). The prototype is synchronous.
- Strategy pattern with a list of callable objects — adds indirection without benefit at this scale.

---

## Decision 4: `process_ticket` Integration

**Decision**: Wrap `process_ticket` to call `SkillsInvoker.run()` first, then use the returned `InvokerResult` fields in place of the current direct module calls.

**Rationale**: Minimal diff. The current `process_ticket` logic is correct; the invoker adds the structured pipeline around it without changing the output contract (`AgentResponse`). This satisfies the constitution's "smallest viable change" principle.

**What changes in `prototype.py`**:
- Import `SkillsInvoker` from `src.agent.skills_invoker`
- Replace the inline `store.resolve_identity()` + `format_response()` + `evaluate_escalation()` + `_kb.search()` calls with `invoker.run(msg)` → unpack `InvokerResult`
- Output: `AgentResponse` is unchanged; only the internals are rerouted through the invoker

---

## Existing Module → Skill Mapping

| Skill | Priority | Existing Function / Method | Module |
|-------|----------|---------------------------|--------|
| Customer Identification | 0 | `ConversationStore.resolve_identity(email, phone)` | `conversation_store.py` |
| Sentiment Analysis | 1 | `ConversationStore.compute_sentiment_trend(conversation)` | `conversation_store.py` |
| Knowledge Retrieval | 2 | `KnowledgeBase.search(query, top_k)` | `knowledge_base.py` |
| Escalation Decision | 3 | `evaluate_escalation(message)` | `escalation_evaluator.py` |
| Channel Adaptation | 4 | `format_response(raw, channel, name)` | `channel_formatter.py` |

All 5 functions exist and are tested (79 tests passing, Phase 2B/2C).

---

## Resolve Identity — Existing Method Confirmed

`ConversationStore.resolve_identity(email: str | None, phone: str | None) → str`

Exists at `conversation_store.py:114`. Returns a stable `customer_key` string. The Customer Identification Skill wraps this plus the follow-up `get_or_create_customer()` call to produce a full `CustomerIdentificationResult`.

---

## Phase 2E Has No External Dependencies

- No new packages required
- No new database tables
- No new MCP tools
- No environment variables
- No API calls beyond existing OpenAI usage in `escalation_evaluator.py`
