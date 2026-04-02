# Implementation Plan: Agent Memory & State (002-memory-state)

**Branch**: `002-memory-state` | **Date**: 2026-04-02 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `/specs/002-memory-state/spec.md`

---

## Summary

Extend the NexaFlow AI support agent from a stateless handler into a stateful conversational system by introducing a `ConversationStore` class that holds all in-memory state: customer profiles, conversation histories, per-message sentiment scores, ticket status transitions, cross-channel identity resolution, and topic tracking. The `process_ticket` function in `prototype.py` gains two store interaction points (pre-processing: load history; post-processing: record state). All 16 Phase 2B tests must continue to pass after integration.

---

## Technical Context

**Language/Version**: Python 3.12  
**Primary Dependencies**: OpenAI (already installed), python-dotenv (already installed) — no new external dependencies  
**Storage**: In-memory only (Python dicts/lists). External persistence explicitly out of scope (deferred to Phase 4A).  
**Testing**: pytest — existing test suite (16 tests) plus new unit tests for `conversation_store.py`  
**Target Platform**: Linux / WSL2 (local development)  
**Project Type**: Single Python package  
**Performance Goals**: p95 < 3 s end-to-end (unchanged from Phase 2B — store ops are O(1)/O(N) dict lookups, negligible)  
**Constraints**: Max 20 messages per conversation; sentiment window N=3; no thread safety required (single-process prototype)  
**Scale/Scope**: ~800 tickets/week simulation; all state is reset on process restart

---

## Constitution Check

*GATE: Must pass before proceeding to tasks.*

| Principle | Check | Status |
|-----------|-------|--------|
| III-2 — Email as primary key | `resolve_identity()` returns email when available; phone-only gets transient key | ✅ PASS |
| III-3 — Channel metadata preserved | Every `Message` stores `channel` and `direction` | ✅ PASS |
| IV-1 — Datetime injection | `prototype.py` already injects PKT datetime; no change to prompts | ✅ PASS |
| IV-3 — Check full cross-channel history | `get_conversation_context()` surfaces full history to LLM | ✅ PASS |
| FR-011 — No cross-customer leakage | All customer data keyed by private dicts; no cross-lookup possible via public API | ✅ PASS |
| FR-012 — In-memory only | `conversation_store.py` has zero external imports beyond stdlib | ✅ PASS |
| SC-007 — 16 Phase 2B tests pass | Store is injectable (default singleton, overridable); existing tests unchanged | ✅ PASS |
| Secrets policy | No new secrets; no new API keys required | ✅ PASS |

**Gate result: PASS — proceed to tasks.**

---

## Project Structure

### Documentation (this feature)

```text
specs/002-memory-state/
├── plan.md              ← this file
├── spec.md              ← feature specification
├── research.md          ← Phase 0: design decisions
├── data-model.md        ← Phase 1: entity definitions
├── quickstart.md        ← Phase 1: integration guide
├── contracts/
│   └── store_interface.py  ← Phase 1: typed API contract stub
└── tasks.md             ← Phase 2 output (/sp.tasks — NOT created here)
```

### Source Code Changes

```text
src/agent/
├── models.py                  MODIFY — add TicketStatus, SentimentLabel, SentimentTrend dataclasses
├── conversation_store.py      NEW — ConversationStore class + get_store() singleton
└── prototype.py               MODIFY — two store interaction points in process_ticket()

tests/
├── test_core_loop.py          NO CHANGE (must still pass)
├── test_escalation_evaluator.py  NO CHANGE (must still pass)
├── test_prototype.py          NO CHANGE (must still pass)
└── unit/
    └── test_conversation_store.py  NEW — unit tests for ConversationStore
```

**Structure Decision**: Single project layout (existing `src/agent/` package). One new module, two modified modules, one new test file. No new directories in `src/`.

---

## Complexity Tracking

No constitution violations. All changes are within the existing single-project structure, add no new external dependencies, and do not exceed any gate constraint.

---

## Phase 0 Research Summary

All design decisions are resolved. See [research.md](research.md) for full rationale.

| Decision | Resolution |
|----------|-----------|
| Primary identity key | Email; phone-only → `phone:<E164>` transient key |
| In-memory structure | Python `dict` + `list` inside `ConversationStore` class |
| Sentiment score source | Proxy from `EscalationDecision.urgency` (see `URGENCY_SCORE_MAP`) |
| Sentiment trend algorithm | Rolling avg + slope over last N=3 inbound scored messages |
| Ticket status transitions | `open→pending`, `open→escalated`, `pending→resolved`, `pending→escalated`; resolved/escalated are terminal |
| Message cap | 20 messages; oldest dropped (no summarization) |
| Topic label source | `NormalizedTicket.inferred_topic` (already produced by `normalize_message`) |
| `process_ticket` integration | Pre-load context (step 1b); post-record state (after step 6) |

---

## Phase 1 Design Artifacts

| Artifact | Path | Status |
|----------|------|--------|
| Data model | `specs/002-memory-state/data-model.md` | ✅ Complete |
| API contract | `specs/002-memory-state/contracts/store_interface.py` | ✅ Complete |
| Integration guide | `specs/002-memory-state/quickstart.md` | ✅ Complete |

---

## Implementation Tasks (summary — full breakdown in tasks.md)

The following task areas will be broken down by `/sp.tasks`:

1. **T1 — models.py extensions**: Add `TicketStatus` enum, `SentimentLabel` enum, `SentimentTrend` dataclass, update `AgentResponse` if needed
2. **T2 — ConversationStore: identity + customer**: `resolve_identity`, `link_phone_to_email`, `get_or_create_customer`, `get_customer`, `get_store` singleton
3. **T3 — ConversationStore: conversation + message**: `get_or_create_conversation`, `get_active_conversation`, `add_message` (20-cap), `Conversation` creation with new `Ticket`
4. **T4 — ConversationStore: ticket management**: `Ticket.transition` (allowed/blocked transitions), `transition_ticket`, `add_topic`, `closed_at` setting
5. **T5 — ConversationStore: derived queries**: `compute_sentiment_trend`, `get_conversation_context`, `has_prior_topic`, `count_topic_contacts`
6. **T6 — prototype.py: pre-processing integration**: Identity resolution, customer/conversation load, context extraction before KB search
7. **T7 — prototype.py: post-processing integration**: Store inbound message, add topic, transition ticket, store outbound message
8. **T8 — Unit tests**: `tests/unit/test_conversation_store.py` — one test per contract method, regression suite for all 16 Phase 2B tests

---

## Risks

- **Sentiment proxy accuracy**: Using `urgency` as a proxy for sentiment score may produce coarse trends. Mitigation: proxy mapping is a named constant (`URGENCY_SCORE_MAP`) so it can be tuned without touching logic.
- **Phone-to-email merge correctness**: Merging transient profiles is a one-way operation; if done incorrectly it could lose topic history. Mitigation: unit test `test_phone_email_merge_preserves_history`.
- **Phase 2B regression**: Modifications to `prototype.py` must not alter existing call signatures or return types. Mitigation: `get_store()` is injected only inside `process_ticket` body; existing 16 tests are run as part of the task acceptance check.
