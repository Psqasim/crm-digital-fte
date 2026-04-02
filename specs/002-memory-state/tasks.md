---
description: "Task list for Phase 2C — Agent Memory & State"
---

# Tasks: 002-memory-state — Agent Memory & State

**Input**: Design documents from `/specs/002-memory-state/`  
**Branch**: `002-memory-state` | **Date**: 2026-04-02  
**Prerequisites**: plan.md ✅ | spec.md ✅ | data-model.md ✅ | contracts/store_interface.py ✅ | ADR-0001 ✅

**Total tasks**: 41 across 8 phases  
**HIGH RISK tasks**: T015, T016, T021, T033 — see flags below

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different concerns, no dependency on each other)
- **[Story]**: Maps to user story from spec.md
- **⚠️ HIGH RISK**: Modifies `prototype.py` core loop or performs irreversible state mutation
- Tests use TDD order: write test first → verify it FAILS → implement → verify it PASSES

---

## Phase 1: Setup (Project Scaffolding)

**Purpose**: Create the two new files that all subsequent tasks depend on.

- [ ] T001 Create `src/agent/conversation_store.py` with file-level docstring, `from __future__ import annotations` import, and a `# TODO: implement` comment block only — no logic yet
- [ ] T002 [P] Create `tests/unit/__init__.py` (empty) and `tests/unit/test_conversation_store.py` with a single `from src.agent.conversation_store import ConversationStore` import and a placeholder `def test_placeholder(): pass` — verify the import resolves cleanly with `python -m pytest tests/unit/test_conversation_store.py -v`

**Checkpoint**: Both files exist, `test_placeholder` passes with 0 errors.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data types and singleton infrastructure that ALL user stories depend on. No user story work begins until this phase is complete.

**⚠️ CRITICAL**: Nothing in Phases 3–7 can start until T003–T006 are done.

- [ ] T003 Add `TicketStatus(str, Enum)` with values `OPEN/PENDING/ESCALATED/RESOLVED` and `SentimentLabel(str, Enum)` with values `IMPROVING/STABLE/DETERIORATING` to `src/agent/models.py` — append after existing dataclasses, do not modify any existing class
- [ ] T004 [P] Add `SentimentTrend` dataclass (`label: SentimentLabel`, `window_scores: list[float]`, `window_size: int = 3`) to `src/agent/models.py` immediately after `SentimentLabel` — do not modify any existing class
- [ ] T005 [P] Add sentinel constants to `src/agent/conversation_store.py`: `MESSAGE_CAP = 20`, `SENTIMENT_WINDOW = 3`, `URGENCY_SCORE_MAP: dict[tuple, float]` mapping `(urgency_str, should_escalate_bool) → float` per data-model.md table, and stub `CustomerProfile`, `Conversation`, `Message`, `Ticket` dataclasses (fields only, no methods yet) importing `TicketStatus`, `SentimentLabel`, `SentimentTrend` from `src.agent.models`
- [ ] T006 Implement `get_store()` singleton factory and `reset_store()` test-helper in `src/agent/conversation_store.py` per ADR-0001 pattern: `_store: ConversationStore | None = None`; `get_store()` lazily constructs; `reset_store()` sets `_store = None` — add `ConversationStore.__init__` that initialises `_customers: dict`, `_conversations: dict`, `_phone_to_email: dict`

**Checkpoint**: `python -c "from src.agent.conversation_store import get_store; s = get_store(); print(type(s))"` prints `<class '...ConversationStore'>` with no errors. All 16 Phase 2B tests still pass: `pytest tests/test_core_loop.py tests/test_escalation_evaluator.py tests/test_prototype.py -v`.

---

## Phase 3: User Story 1 — Multi-Turn Conversation (Priority: P1) 🎯 MVP

**Goal**: A customer's full conversation history is stored and retrieved, and the agent receives prior context when generating the response for any follow-up message.

**Independent Test**: Send two `TicketMessage` objects with the same `customer_email`. Verify the second call to `process_ticket` produces a formatted response that includes content referencing the first message's context (injected via `get_conversation_context`).

### Tests for User Story 1 (write FIRST — must FAIL before T011)

- [ ] T007 [US1] Write `test_get_or_create_customer_creates_on_first_call` and `test_get_or_create_customer_returns_same_on_second_call` in `tests/unit/test_conversation_store.py` — assert same object returned on duplicate key; assert `channels_used` updated
- [ ] T008 [P] [US1] Write `test_get_or_create_conversation_creates_new_for_new_customer` in `tests/unit/test_conversation_store.py` — assert `Conversation.ticket.status == TicketStatus.OPEN`; assert conversation_id appended to `CustomerProfile.conversation_ids`
- [ ] T009 [P] [US1] Write `test_add_message_cap_enforced_at_20` in `tests/unit/test_conversation_store.py` — add 21 messages; assert `len(conversation.messages) == 20`; assert `conversation.messages[0].text == "msg 1"` (msg 0 was dropped)
- [ ] T010 [P] [US1] Write `test_get_conversation_context_returns_formatted_string` in `tests/unit/test_conversation_store.py` — add 2 messages (1 inbound, 1 outbound); assert returned string contains `[INBOUND` and `[OUTBOUND` prefixes; assert empty string when no active conversation

### Implementation for User Story 1

- [ ] T011 [US1] Implement `get_or_create_customer(key, name, channel) → CustomerProfile` and `get_customer(key) → CustomerProfile | None` in `src/agent/conversation_store.py` — store in `_customers[key]`; `get_customer` returns `None` for unknown keys (never raises)
- [ ] T012 [US1] Implement `get_or_create_conversation(customer_key, channel) → Conversation` and `get_active_conversation(customer_key) → Conversation | None` in `src/agent/conversation_store.py` — active = most recent conversation whose ticket status is not `RESOLVED`; creates new `Conversation` + `Ticket(status=OPEN)` when no active conversation found; stores in `_conversations[conv_id]`
- [ ] T013 [US1] Implement `add_message(conversation_id, message) → None` in `src/agent/conversation_store.py` — enforce `MESSAGE_CAP`: if `len(messages) == MESSAGE_CAP` before append, drop `messages[0]`; update `conversation.updated_at`
- [ ] T014 [US1] Implement `get_conversation_context(customer_key) → str` in `src/agent/conversation_store.py` — format each message as `[INBOUND | <timestamp>] <text>` or `[OUTBOUND | <timestamp>] <text>`; join with newline; return empty string if no active conversation; postcondition: output contains only this customer's data
- [ ] T015 ⚠️ HIGH RISK [US1] Add pre-processing store integration to `process_ticket` in `src/agent/prototype.py` — insert after `normalize_message()` call: `store = get_store()`, `customer_key = store.resolve_identity(email, phone)` (stub call — `resolve_identity` not yet implemented, call `email or f"phone:{phone}"` directly until T020), `customer = store.get_or_create_customer(...)`, `conversation = store.get_or_create_conversation(...)`, `conversation_context = store.get_conversation_context(customer_key)`, `prior_topic = store.has_prior_topic(customer_key, ticket.inferred_topic)` (stub returning False until T037); inject `conversation_context` into `user_content` before OpenAI call — **run all 16 Phase 2B tests after this task; they MUST pass**
- [ ] T016 ⚠️ HIGH RISK [US1] Add post-processing store writes to `process_ticket` in `src/agent/prototype.py` — after response generated (both escalation path and normal path): construct inbound `Message(direction="inbound", sentiment_score=None)` and outbound `Message(direction="outbound", sentiment_score=None)`; call `store.add_message(conversation.id, inbound_msg)` then `store.add_message(conversation.id, outbound_msg)`; call `store.transition_ticket(conversation.id, TicketStatus.PENDING)` on normal path — **run all 16 Phase 2B tests after this task; they MUST pass**

**Checkpoint**: US1 complete. Two-message flow works end-to-end: second call receives history context. All 16 Phase 2B tests still pass.

---

## Phase 4: User Story 2 — Cross-Channel Identity Recognition (Priority: P2)

**Goal**: A customer contacting via WhatsApp with a phone number that maps to a known email receives their existing conversation history, not a blank slate.

**Independent Test**: Create a customer via email. Call `link_phone_to_email(phone, email)`. Then call `process_ticket` with a WhatsApp `TicketMessage` carrying only that phone number. Verify `get_customer(email)` returns the same profile and the WhatsApp message appears in the same conversation history.

### Tests for User Story 2 (write FIRST — must FAIL before T020)

- [ ] T017 [P] [US2] Write `test_resolve_identity_email_only` (returns email), `test_resolve_identity_phone_only_unmapped` (returns `"phone:+923001234567"`), `test_resolve_identity_both_returns_email` in `tests/unit/test_conversation_store.py`
- [ ] T018 [P] [US2] Write `test_link_phone_creates_mapping` and `test_link_phone_to_email_merges_transient_profile` in `tests/unit/test_conversation_store.py` — transient merge test: create customer under `"phone:+923001234567"` with 1 conversation; call `link_phone_to_email`; assert conversation appears under email key; assert transient key no longer exists in `_customers`
- [ ] T019 [P] [US2] Write `test_cross_channel_history_continuity` in `tests/unit/test_conversation_store.py` — simulate email message → link phone → WhatsApp message; assert both messages in same conversation history

### Implementation for User Story 2

- [ ] T020 [P] [US2] Implement `resolve_identity(email, phone) → str` in `src/agent/conversation_store.py` — resolution order: (1) email provided → return email + add phone mapping if phone also provided; (2) phone only → check `_phone_to_email` → return mapped email if found; (3) return `f"phone:{phone}"`; precondition: at least one of email/phone must be non-None non-empty — **update the stub in T015's code to call this method**
- [ ] T021 ⚠️ HIGH RISK [US2] Implement `link_phone_to_email(phone, email) → None` in `src/agent/conversation_store.py` — (1) add `_phone_to_email[phone] = email`; (2) if `f"phone:{phone}"` key exists in `_customers`: copy `known_phones`, `conversation_ids`, `topic_history` into email-keyed profile (create if not exists); delete transient key — this is irreversible; test `test_link_phone_to_email_merges_transient_profile` MUST pass before committing

### User Story 2 Integration Note

- [ ] T022 [US2] Update pre-processing block in `src/agent/prototype.py` (T015 code) to attempt email extraction from `ticket.message` via `re.findall(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}", msg)` when customer_key is a transient `phone:` key — if email found in message text, call `store.link_phone_to_email(phone, extracted_email)` and re-resolve `customer_key` to the email — **run all 16 Phase 2B tests after this task**

**Checkpoint**: US2 complete. Phone-only customer mapped to email gets unified history. All tests pass.

---

## Phase 5: User Story 3 — Sentiment Trend Awareness (Priority: P3)

**Goal**: The agent tracks whether a customer's frustration is growing across messages and surfaces a `DETERIORATING` trend signal before escalation decisions.

**Independent Test**: Add 3 inbound messages with descending sentiment scores (0.80, 0.25, 0.05). Call `compute_sentiment_trend`. Assert label is `DETERIORATING`. Then add 1 message with score 0.90. Re-compute. Assert label is no longer `DETERIORATING`.

### Tests for User Story 3 (write FIRST — must FAIL before T026)

- [ ] T023 [P] [US3] Write `test_compute_sentiment_trend_deteriorating` (mean < 0.35, slope < 0) and `test_compute_sentiment_trend_improving` (mean > 0.65, slope > 0.2) in `tests/unit/test_conversation_store.py`
- [ ] T024 [P] [US3] Write `test_compute_sentiment_trend_stable_insufficient_data` (fewer than 2 scored inbound messages → `STABLE`) and `test_compute_sentiment_trend_stable_mixed` (mixed scores that do not meet thresholds → `STABLE`) in `tests/unit/test_conversation_store.py`
- [ ] T025 [P] [US3] Write `test_sentiment_recovery_resets_trend` in `tests/unit/test_conversation_store.py` — add 3 low-score messages, verify `DETERIORATING`; add 1 high-score message; re-compute with window=3; verify no longer `DETERIORATING`

### Implementation for User Story 3

- [ ] T026 [US3] Implement `compute_sentiment_trend(conversation) → SentimentTrend` in `src/agent/conversation_store.py` — extract last `SENTIMENT_WINDOW` inbound messages with non-None `sentiment_score`; if fewer than 2: return `SentimentTrend(STABLE, [])`; compute mean + slope (`scores[-1] - scores[0]`); apply thresholds from data-model.md
- [ ] T027 [US3] Update `add_message` in `src/agent/conversation_store.py` to accept and store `sentiment_score: float | None` on inbound `Message` objects — update post-processing in `src/agent/prototype.py` (T016 code) to derive `sentiment_score` from `URGENCY_SCORE_MAP[(escalation.urgency, escalation.should_escalate)]` and set it on the inbound `Message` before calling `store.add_message` — **run all 16 Phase 2B tests after this task**

**Checkpoint**: US3 complete. `compute_sentiment_trend` returns correct label for constructed test sequences. All tests pass.

---

## Phase 6: User Story 4 — Resolution Status Tracking (Priority: P3)

**Goal**: Ticket status transitions are enforced. A resolved ticket cannot be re-opened; a new question from the same customer opens a fresh ticket.

**Independent Test**: Create a ticket; transition to `PENDING` then `RESOLVED`. Attempt `store.transition_ticket(conv_id, TicketStatus.OPEN)` — assert `ValueError` raised. Then call `get_or_create_conversation` — assert a brand-new conversation ID is returned (not the old one).

### Tests for User Story 4 (write FIRST — must FAIL before T031)

- [ ] T028 [P] [US4] Write `test_ticket_transition_open_to_pending`, `test_ticket_transition_open_to_escalated`, `test_ticket_transition_pending_to_resolved`, `test_ticket_transition_pending_to_escalated` in `tests/unit/test_conversation_store.py` — all valid paths
- [ ] T029 [P] [US4] Write `test_ticket_transition_resolved_raises`, `test_ticket_transition_escalated_raises`, `test_ticket_transition_pending_to_open_raises` in `tests/unit/test_conversation_store.py` — all invalid paths must raise `ValueError`
- [ ] T030 [P] [US4] Write `test_resolved_ticket_creates_new_conversation` in `tests/unit/test_conversation_store.py` — resolve a ticket; call `get_or_create_conversation` again; assert new `conv.id != old_conv.id`; assert new ticket status is `OPEN`

### Implementation for User Story 4

- [ ] T031 [US4] Implement `Ticket.transition(new_status: TicketStatus) → None` as a method on the `Ticket` dataclass in `src/agent/conversation_store.py` — allowed matrix: `open→pending`, `open→escalated`, `pending→resolved`, `pending→escalated`; all others raise `ValueError("Invalid transition: {self.status} → {new_status}")`; set `self.status = new_status`
- [ ] T032 [US4] Implement `transition_ticket(conversation_id, new_status) → None` in `src/agent/conversation_store.py` — call `conversation.ticket.transition(new_status)`; set `conversation.ticket.closed_at = utcnow()` when `new_status in (RESOLVED, ESCALATED)`; raise `KeyError` if `conversation_id` not found
- [ ] T033 ⚠️ HIGH RISK [US4] Update escalation short-circuit path in `process_ticket` in `src/agent/prototype.py` to call `store.transition_ticket(conversation.id, TicketStatus.ESCALATED)` after recording inbound message (replace the `TicketStatus.PENDING` call on the escalation path); verify `conversation.ticket.closed_at` is set — **run all 16 Phase 2B tests after this task; they MUST pass**

**Checkpoint**: US4 complete. Status machine enforced. Resolved tickets spawn new conversations. All tests pass.

---

## Phase 7: User Story 5 — Topic History and Repeat Issue Detection (Priority: P4)

**Goal**: A customer who raises the same topic across multiple sessions gets a response that acknowledges prior contact and skips already-attempted steps.

**Independent Test**: Create customer; open conversation A; call `add_topic(conv_a, "workflow-triggers")`. Resolve ticket. Open conversation B. Assert `has_prior_topic(email, "workflow-triggers")` is `True`. Assert `count_topic_contacts(email, "workflow-triggers")` returns 1. Process a ticket with `inferred_topic="workflow-triggers"` — assert `prior_note` appears in the injected LLM content.

### Tests for User Story 5 (write FIRST — must FAIL before T037)

- [ ] T034 [P] [US5] Write `test_add_topic_dedup_within_conversation` in `tests/unit/test_conversation_store.py` — call `add_topic` twice with the same topic on the same conversation; assert `Ticket.topics` has it once; assert `CustomerProfile.topic_history[topic]` has conversation_id once
- [ ] T035 [P] [US5] Write `test_has_prior_topic_true_and_false` in `tests/unit/test_conversation_store.py` — add topic to conv A; assert `has_prior_topic` True; check different topic → False
- [ ] T036 [P] [US5] Write `test_count_topic_contacts_across_sessions` in `tests/unit/test_conversation_store.py` — two separate conversations both raise "billing-dispute"; assert count = 2

### Implementation for User Story 5

- [ ] T037 [P] [US5] Implement `add_topic(conversation_id, topic) → None`, `has_prior_topic(customer_key, topic) → bool`, and `count_topic_contacts(customer_key, topic) → int` in `src/agent/conversation_store.py` — `add_topic`: append topic to `Ticket.topics` only if not already present; append `conversation_id` to `CustomerProfile.topic_history[topic]` only if not already present; `has_prior_topic`: check `len(CustomerProfile.topic_history.get(topic, [])) > 0`; `count_topic_contacts`: return `len(CustomerProfile.topic_history.get(topic, []))`
- [ ] T038 [US5] Update pre-processing block in `src/agent/prototype.py` (T015 code): replace `prior_topic = store.has_prior_topic(...)` stub with real call; build `prior_note` string: `f"\n\nNote: This customer has contacted us about '{ticket.inferred_topic}' {count} time(s) before. Skip basic troubleshooting steps already attempted."` when `has_prior_topic` is True; append `prior_note` to `user_content` before OpenAI call — also call `store.add_topic(conversation.id, ticket.inferred_topic)` in post-processing (T016 code) — **run all 16 Phase 2B tests after this task**

**Checkpoint**: US5 complete. Repeat topic detection works across sessions. Prior note injected into LLM context. All tests pass.

---

## Phase 8: Polish & Regression (Cross-Cutting)

**Purpose**: Security isolation test, integration regression guard, and test infrastructure polish.

- [ ] T039 [P] Write `test_no_cross_customer_data_leakage` in `tests/unit/test_conversation_store.py` — create customers Alice and Bob with separate histories; assert `store.get_customer("alice@ex.com")` returns Alice's data only; assert `store.get_conversation_context("alice@ex.com")` contains no reference to Bob's messages; assert `store.get_customer("bob@ex.com").conversation_ids` does not overlap with Alice's — **FR-011 hard requirement, zero tolerance**
- [ ] T040 [P] Write `test_sentiment_score_proxy_all_urgency_levels` in `tests/unit/test_conversation_store.py` — verify all four keys in `URGENCY_SCORE_MAP` produce correct float values: `("high", True)→0.05`, `("normal", True)→0.25`, `("low", True)→0.45`, `(None, False)→0.80`
- [ ] T041 Run full regression suite and verify all 41 unit tests + all 16 Phase 2B tests pass: `pytest tests/unit/test_conversation_store.py tests/test_core_loop.py tests/test_escalation_evaluator.py tests/test_prototype.py -v` — record PASS count in this file's Phase 8 checkpoint comment

**Final Checkpoint**: 52 total tests pass (31 unit + 5 cross-channel + 16 Phase 2B regression). Zero cross-customer data leakage. All `process_ticket` call signatures unchanged.
<!-- PASS COUNT: 52 passed (2026-04-02) — pytest tests/unit/test_conversation_store.py tests/test_cross_channel.py tests/test_core_loop.py tests/test_escalation_evaluator.py tests/test_prototype.py -->

---

## Dependency Graph

```
Phase 1 (T001–T002)
    ↓
Phase 2 (T003–T006)   ← ALL user stories blocked until complete
    ↓
Phase 3 US1 (T007–T016)   ← P1 — start immediately after Phase 2
    ↓
Phase 4 US2 (T017–T022)   ← P2 — start after Phase 3 (resolve_identity used in T015)
    ↓
Phase 5 US3 (T023–T027)   ← P3 — start after Phase 3 (uses add_message from T013)
Phase 6 US4 (T028–T033)   ← P3 — start after Phase 3 (uses Ticket from T006)
    ↓
Phase 7 US5 (T034–T038)   ← P4 — start after Phase 3 (uses conversation + customer)
    ↓
Phase 8 Polish (T039–T041) ← after all stories complete
```

**Note**: US3 and US4 are both P3 and can run in parallel with each other (US3 = `conversation_store.py` sentiment methods; US4 = `conversation_store.py` ticket methods — different methods, no overlap).

### Prototype.py Change Sequence (STRICTLY SEQUENTIAL — same function)

T015 → T016 → T022 → T027 → T033 → T038

All six are modifications to `process_ticket`. Each builds on the previous. Never interleave.

---

## Parallel Opportunities

### Phase 2 (Foundational)
```
T003 models.py extensions       ─┐
T004 SentimentTrend dataclass   ─┤ parallel (same file, sequential recommended)
T005 ConversationStore skeleton ─┘ (different file from T003/T004 — truly parallel)
```

### Phase 3 US1 Tests (can be written in any order)
```
T007 customer tests
T008 conversation tests    } all in test_conversation_store.py — write sequentially
T009 message cap test      } but logically independent
T010 context format test
```

### Phase 5 US3 + Phase 6 US4 (truly parallel — different methods in same file)
```
Agent A: T023→T024→T025→T026→T027 (sentiment)
Agent B: T028→T029→T030→T031→T032→T033 (ticket status)
```

---

## Implementation Strategy

### MVP First (User Story 1 only — ~16 tasks)

1. Complete Phase 1 + Phase 2 (T001–T006) — foundation
2. Complete Phase 3 US1 (T007–T016) — multi-turn conversation working
3. **STOP and VALIDATE**: Run `pytest tests/unit/test_conversation_store.py tests/test_prototype.py -v`
4. Demo: two sequential calls to `process_ticket` with same email show context in second response

### Incremental Delivery (one phase per session)

| Session | Phase | Delivers |
|---------|-------|---------|
| 1 | Phase 1+2+3 | Multi-turn conversation (MVP) |
| 2 | Phase 4 | Cross-channel identity |
| 3 | Phase 5+6 | Sentiment trend + status tracking |
| 4 | Phase 7 | Topic history + repeat detection |
| 5 | Phase 8 | Regression + polish |

---

## Task Summary

| Phase | Tasks | Story | HIGH RISK |
|-------|-------|-------|-----------|
| 1 Setup | T001–T002 | — | — |
| 2 Foundational | T003–T006 | — | — |
| 3 US1 Multi-Turn | T007–T016 | P1 | T015, T016 |
| 4 US2 Cross-Channel | T017–T022 | P2 | T021 |
| 5 US3 Sentiment | T023–T027 | P3 | — |
| 6 US4 Status | T028–T033 | P3 | T033 |
| 7 US5 Topics | T034–T038 | P4 | — |
| 8 Polish | T039–T041 | — | — |
| **TOTAL** | **41** | **5 stories** | **4 tasks** |

**HIGH RISK guard**: Before committing any task marked ⚠️ HIGH RISK, run:
```bash
pytest tests/test_core_loop.py tests/test_escalation_evaluator.py tests/test_prototype.py -v
```
All 16 must pass. If any fail, do NOT commit — diagnose and fix first.
