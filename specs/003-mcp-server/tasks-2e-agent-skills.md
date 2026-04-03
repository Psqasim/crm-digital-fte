---
description: "Phase 2E — Agent Skills Definition + Wiring task list"
---

# Tasks: Phase 2E — Agent Skills (003-mcp-server)

**Branch**: `003-mcp-server`
**Input**: `specs/003-mcp-server/plan-2e-agent-skills.md`, `specs/003-mcp-server/spec-2e-agent-skills.md`
**Prerequisites**: plan-2e (done), spec-2e (done), data-model-2e (done), contracts/skills_invoker_contract.py (done)
**Current test state**: 79/79 tests passing — MUST stay green after every task
**Constraint**: No new business logic, no new packages, no new MCP tools — wiring only

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify all existing target functions are importable and available before wiring.

- [ ] T001 Confirm all 5 target functions are importable: `resolve_identity` (conversation_store.py:114), `compute_sentiment_trend` (conversation_store.py:268), `KnowledgeBase.search` (knowledge_base.py:66), `evaluate_escalation` (escalation_evaluator.py:64), `format_response` (channel_formatter.py:17)

  **Acceptance criteria**: Run `python -c "from src.agent.conversation_store import ConversationStore; from src.agent.knowledge_base import KnowledgeBase; from src.agent.escalation_evaluator import evaluate_escalation; from src.agent.channel_formatter import format_response; print('OK')"` exits 0.

  **Dependencies**: None
  **Test needed**: No (verification only)
  **Risk**: LOW

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create the `SkillManifest` dataclass and `SKILLS` constants that all downstream modules depend on. No other phase can start until T002 is done.

**⚠️ CRITICAL**: T003–T010 all import from `skills_manifest.py` — do not start them until T002 is complete.

- [ ] T002 Create `src/agent/skills_manifest.py` — `SkillManifest` frozen dataclass + 5 constants + `SKILLS` list

  **File**: `src/agent/skills_manifest.py` (new file)

  **Exact content to produce**:
  ```python
  from __future__ import annotations
  from dataclasses import dataclass, field

  @dataclass(frozen=True)
  class SkillManifest:
      skill_id: str
      name: str
      version: str
      priority: int          # 0 = first, 4 = last
      trigger: str
      connected_tools: list[str] = field(default_factory=list)
      guardrails: list[str] = field(default_factory=list)
  ```

  Five module-level constants:
  - `CUSTOMER_IDENTIFICATION` — skill_id=`customer_identification_v1`, priority=0
  - `SENTIMENT_ANALYSIS` — skill_id=`sentiment_analysis_v1`, priority=1
  - `KNOWLEDGE_RETRIEVAL` — skill_id=`knowledge_retrieval_v1`, priority=2
  - `ESCALATION_DECISION` — skill_id=`escalation_decision_v1`, priority=3
  - `CHANNEL_ADAPTATION` — skill_id=`channel_adaptation_v1`, priority=4

  `SKILLS: list[SkillManifest]` = list of the 5 constants above (in priority order).

  Each constant's `trigger` field: copy the one-line trigger description from `spec-2e-agent-skills.md` for that skill.
  Each constant's `connected_tools` field: list of strings from that skill's `connected_tools:` section in spec.
  Each constant's `guardrails` field: list of strings from that skill's `guardrails:` section in spec.

  **Acceptance criteria**:
  - `from src.agent.skills_manifest import SKILLS, CUSTOMER_IDENTIFICATION` imports without error.
  - `len(SKILLS) == 5`
  - `SKILLS[0].skill_id == "customer_identification_v1"` and `SKILLS[0].priority == 0`
  - `SKILLS[4].skill_id == "channel_adaptation_v1"` and `SKILLS[4].priority == 4`
  - All 5 dataclass instances are frozen (attempting `CUSTOMER_IDENTIFICATION.priority = 99` raises `FrozenInstanceError`)

  **Dependencies**: T001
  **Test needed**: Yes (T010 covers this)
  **Risk**: LOW

**Checkpoint**: `skills_manifest.py` importable — foundational for all subsequent tasks.

---

## Phase 3: User Story 5 — Customer Identification (Priority: P1, Skill priority 0)

**Goal**: Wrap `ConversationStore.resolve_identity()` as a skill, expose `CustomerIdentificationResult` with `customer_id`, `is_returning_customer`, `customer_plan`, `resolution_action`.

**Independent Test**: Import `SkillsInvoker`, call `run()` with a TicketMessage whose email is unknown; verify `customer_id_result.is_returning_customer == False` and `resolution_action == "created_new"`.

- [ ] T003 [P] Create result dataclasses in `src/agent/skills_invoker.py` — `CustomerIdentificationResult`, `SentimentAnalysisResult`, `KnowledgeRetrievalResult`, `EscalationDecisionResult`, `ChannelAdaptationResult`, `InvokerResult`

  **File**: `src/agent/skills_invoker.py` (new file — skeleton only, no method bodies yet)

  Create the 6 result dataclasses matching the schemas in `specs/003-mcp-server/data-model-2e.md` and `specs/003-mcp-server/contracts/skills_invoker_contract.py`. Add `SkillsInvoker` class stub with method signatures (no bodies — `raise NotImplementedError`).

  **Acceptance criteria**:
  - `from src.agent.skills_invoker import SkillsInvoker, InvokerResult, CustomerIdentificationResult` imports without error.
  - `CustomerIdentificationResult(customer_id="x", is_returning_customer=False, customer_plan="starter", resolution_action="created_new")` instantiates without error.
  - `InvokerResult` has fields: `customer_id_result`, `sentiment_result`, `kb_result`, `escalation_result`, `channel_result`.

  **Dependencies**: T002
  **Test needed**: Yes (T010 covers this)
  **Risk**: LOW

- [ ] T004 [US5] Implement `SkillsInvoker._run_customer_identification(msg)` in `src/agent/skills_invoker.py`

  **File**: `src/agent/skills_invoker.py` (modify stub from T003)

  **Logic** (no new business logic — wrap existing calls):
  ```python
  def _run_customer_identification(self, msg: TicketMessage) -> CustomerIdentificationResult:
      store = get_store()
      customer_key = store.resolve_identity(
          email=ticket.customer_email,
          phone=ticket.customer_phone,
      )
      # Phone-to-email extraction (preserve T022 logic from prototype.py:153-162)
      # get_or_create_customer(...)
      is_returning = len(store.get_conversation_context(customer_key).strip()) > 0
      # customer_plan: read from CustomerProfile.plan if it exists, else "unknown"
      # resolution_action: "matched_existing" if is_returning else "created_new"
      return CustomerIdentificationResult(
          customer_id=customer_key,
          is_returning_customer=is_returning,
          customer_plan=...,
          resolution_action=...,
      )
  ```

  Copy the phone-to-email extraction logic verbatim from `src/agent/prototype.py:153–162` — do not rewrite it.

  **Acceptance criteria**:
  - `_run_customer_identification` with a new email returns `is_returning_customer=False`, `resolution_action="created_new"`.
  - `_run_customer_identification` called twice with the same email returns `is_returning_customer=True` on the second call, `resolution_action="matched_existing"`.
  - Does not raise if `customer_email` and `customer_phone` are both `None` (anonymous session).

  **Dependencies**: T003
  **Test needed**: Yes (T010 covers this)
  **Risk**: LOW

**Checkpoint**: Customer Identification skill functional in isolation.

---

## Phase 4: User Story 2 — Sentiment Analysis (Priority: P1, Skill priority 1)

**Goal**: Wrap `ConversationStore.compute_sentiment_trend()` as a skill, expose `SentimentAnalysisResult` with `sentiment_score`, `sentiment_label`, `trend_label`, `escalation_recommended`, `data_points_used`.

**Independent Test**: Create a conversation with 3 negative messages, call `_run_sentiment_analysis`; verify `trend_label == "deteriorating"` and `escalation_recommended == True`.

- [ ] T005 [US2] Implement `SkillsInvoker._run_sentiment_analysis(msg, cid_result)` in `src/agent/skills_invoker.py`

  **File**: `src/agent/skills_invoker.py`

  **Logic**:
  ```python
  def _run_sentiment_analysis(self, msg: TicketMessage, cid: CustomerIdentificationResult) -> SentimentAnalysisResult:
      store = get_store()
      conversation = store.get_or_create_conversation(cid.customer_id, msg.channel.value)
      trend: SentimentTrend = store.compute_sentiment_trend(conversation)
      # Map SentimentTrend → SentimentAnalysisResult:
      #   trend.label → trend_label (use .value for enum)
      #   trend.scores → average for sentiment_score
      #   escalation_recommended = trend.label == SentimentLabel.DETERIORATING or avg_score < -0.6
      #   data_points_used = len(trend.scores)
      return SentimentAnalysisResult(...)
  ```

  Map `SentimentTrend` fields from `src/agent/models.py` — do not create new sentiment logic.

  **Acceptance criteria**:
  - Returns `trend_label="insufficient_data"` when conversation has 0 prior messages.
  - Returns `escalation_recommended=True` when conversation has 3+ messages all with scores < -0.5.
  - `data_points_used` equals the number of prior sentiment scores in the conversation.

  **Dependencies**: T004
  **Test needed**: Yes (T010 covers this)
  **Risk**: LOW

**Checkpoint**: Sentiment Analysis skill functional; escalation_recommended flag available for downstream.

---

## Phase 5: User Story 1 — Knowledge Retrieval (Priority: P1, Skill priority 2)

**Goal**: Wrap `KnowledgeBase.search()` as a conditional skill that fires only when the message is classified as a product question. Returns `KnowledgeRetrievalResult` with `results` and `result_count`.

**Independent Test**: Call `_run_knowledge_retrieval` with a message containing "How do I connect NexaFlow to Slack?"; verify `result_count >= 1` and `results[0].relevance_score > 0.0`.

- [ ] T006 [US1] Implement `SkillsInvoker._run_knowledge_retrieval(msg)` in `src/agent/skills_invoker.py`

  **File**: `src/agent/skills_invoker.py`

  **Logic**:
  ```python
  def _run_knowledge_retrieval(self, msg: TicketMessage) -> KnowledgeRetrievalResult:
      # Reuse the same query construction as prototype.py:177:
      #   query = ticket.inferred_topic + " " + ticket.message[:200]
      # Call self._kb.search(query, top_k=3)
      # If results empty → return KnowledgeRetrievalResult(results=[], result_count=0)
      results = self._kb.search(...)
      return KnowledgeRetrievalResult(results=results, result_count=len(results))
  ```

  `self._kb` is a `KnowledgeBase` instance initialised once in `SkillsInvoker.__init__`. Copy the KB instantiation from `prototype.py` (the module-level `_kb = KnowledgeBase()` pattern).

  **Acceptance criteria**:
  - Returns `KnowledgeRetrievalResult(results=[], result_count=0)` — never raises — when query matches nothing.
  - Returns `result_count >= 1` for a known product query string ("slack integration").
  - Empty query string (`msg.message == ""`) returns empty results, not an error.

  **Dependencies**: T005
  **Test needed**: Yes (T010 covers this)
  **Risk**: LOW

**Checkpoint**: Knowledge Retrieval skill functional; results available for LLM prompt construction.

---

## Phase 6: User Story 3 — Escalation Decision (Priority: P2, Skill priority 3)

**Goal**: Wrap `evaluate_escalation()` as a skill, augment with `sentiment_result.escalation_recommended`, expose `EscalationDecisionResult` with `should_escalate`, `reason`, `urgency`.

**Independent Test**: Call `_run_escalation_decision` with a message containing "I am going to sue NexaFlow"; verify `should_escalate=True` and `urgency="critical"`.

- [ ] T007 [US3] Implement `SkillsInvoker._run_escalation_decision(msg, sentiment_result)` in `src/agent/skills_invoker.py`

  **File**: `src/agent/skills_invoker.py`

  **Logic**:
  ```python
  def _run_escalation_decision(self, msg: TicketMessage, sent: SentimentAnalysisResult) -> EscalationDecisionResult:
      # Call existing evaluate_escalation(msg.message) → EscalationDecision
      escalation: EscalationDecision = evaluate_escalation(msg.message)
      # Supplement: if sent.escalation_recommended and not escalation.should_escalate:
      #   override should_escalate=True, reason="Sentiment trend: deteriorating", urgency="high"
      # Map EscalationDecision.urgency (str) to EscalationDecisionResult.urgency
      return EscalationDecisionResult(
          should_escalate=escalation.should_escalate or sent.escalation_recommended,
          reason=escalation.reason if escalation.should_escalate else ("Deteriorating sentiment trend" if sent.escalation_recommended else None),
          urgency=escalation.urgency if escalation.should_escalate else ("high" if sent.escalation_recommended else None),
      )
  ```

  **Acceptance criteria**:
  - `should_escalate=True` when message contains explicit threat keyword defined in `context/escalation-rules.md`.
  - `should_escalate=True` when `sentiment_result.escalation_recommended=True` even if `evaluate_escalation` returns `False`.
  - `should_escalate=False`, `reason=None`, `urgency=None` for a benign message with stable sentiment.

  **Dependencies**: T006
  **Test needed**: Yes (T010 covers this)
  **Risk**: LOW

**Checkpoint**: Escalation Decision skill functional; early-exit path available to invoker.

---

## Phase 7: User Story 4 — Channel Adaptation (Priority: P1, Skill priority 4)

**Goal**: Wrap `format_response()` as a skill, expose `ChannelAdaptationResult` with `formatted_response`, `channel_applied`, `formatting_notes`. Enforce: email=formal+signature, whatsapp≤3 sentences, web_form=semi-formal.

**Independent Test**: Call `apply_channel_adaptation` with a 10-sentence response and `channel="whatsapp"`; verify `formatted_response` contains at most 3 sentences and `"truncated"` appears in `formatting_notes`.

- [ ] T008 [US4] Implement `SkillsInvoker.apply_channel_adaptation(result, raw, channel, name)` in `src/agent/skills_invoker.py`

  **File**: `src/agent/skills_invoker.py`

  **Logic**:
  ```python
  def apply_channel_adaptation(
      self, result: InvokerResult, raw_response: str,
      channel: str, customer_name: str,
  ) -> InvokerResult:
      if result.escalation_result.should_escalate:
          raise ValueError("apply_channel_adaptation called when should_escalate=True")
      from src.agent.models import Channel as ChannelEnum
      ch = ChannelEnum(channel) if isinstance(channel, str) else channel
      formatted = format_response(raw_response, ch, customer_name)
      notes = _build_formatting_notes(raw_response, formatted, ch)
      channel_result = ChannelAdaptationResult(
          formatted_response=formatted,
          channel_applied=ch.value,
          formatting_notes=notes,
      )
      from dataclasses import replace
      return replace(result, channel_result=channel_result)
  ```

  `_build_formatting_notes(original, formatted, channel)` — private helper that produces a list of strings describing what changed (e.g., `["truncated to 3 sentences", "removed signature"]`). Keep simple: compare sentence count and presence of "NexaFlow Support" in output.

  **Acceptance criteria**:
  - Raises `ValueError` if `result.escalation_result.should_escalate=True`.
  - Returns `InvokerResult` with `channel_result` populated; all other fields unchanged.
  - `channel_applied` echoes the channel string used.
  - `formatting_notes` is a list (may be empty for web_form with short responses, but never `None`).

  **Dependencies**: T007
  **Test needed**: Yes (T010 covers this)
  **Risk**: LOW

**Checkpoint**: Channel Adaptation skill functional; all 5 skill adapter methods complete.

---

## Phase 8: Foundational Completion — Invoker Pipeline Assembly

**Purpose**: Wire skills 0→4 into `SkillsInvoker.run()` and create `SkillsRegistry`. These complete the invoker module.

- [ ] T009a [P] Create `src/agent/skills_registry.py` — `SkillsRegistry` class with `get_skill(skill_id)` and `list_skills()`

  **File**: `src/agent/skills_registry.py` (new file)

  **Logic**:
  ```python
  from src.agent.skills_manifest import SKILLS, SkillManifest

  class SkillsRegistry:
      def __init__(self) -> None:
          self._registry: dict[str, SkillManifest] = {s.skill_id: s for s in SKILLS}

      def get_skill(self, skill_id: str) -> SkillManifest:
          return self._registry[skill_id]  # raises KeyError if not found

      def list_skills(self) -> list[SkillManifest]:
          return sorted(self._registry.values(), key=lambda s: s.priority)

  _registry: SkillsRegistry | None = None

  def get_registry() -> SkillsRegistry:
      global _registry
      if _registry is None:
          _registry = SkillsRegistry()
      return _registry
  ```

  **Acceptance criteria**:
  - `get_registry().get_skill("customer_identification_v1")` returns the manifest without error.
  - `get_registry().get_skill("nonexistent")` raises `KeyError`.
  - `get_registry().list_skills()` returns 5 items in priority order 0→4.

  **Dependencies**: T002
  **Test needed**: Yes (T010 covers this)
  **Risk**: LOW

- [ ] T009b [P] Implement `SkillsInvoker.__init__()` and `SkillsInvoker.run()` in `src/agent/skills_invoker.py`

  **File**: `src/agent/skills_invoker.py`

  **`__init__`**: Initialise `self._kb = KnowledgeBase()` (same pattern as prototype.py module-level `_kb`).

  **`run(msg)`** — sequentially calls `_run_customer_identification` → `_run_sentiment_analysis` → `_run_knowledge_retrieval` → `_run_escalation_decision`, returns `InvokerResult` with `channel_result=None`.

  Note: `_run_knowledge_retrieval` is always called (not conditional here); the result may be an empty `KnowledgeRetrievalResult`. Conditionality on whether to use KB results is the LLM's decision in `process_ticket`.

  **Acceptance criteria**:
  - `SkillsInvoker().run(msg)` returns `InvokerResult` with all 4 non-channel fields populated.
  - `channel_result` is `None` on the returned `InvokerResult`.
  - Calling `run()` twice with the same `msg` returns consistent results (idempotent for the same store state).

  **Dependencies**: T004, T005, T006, T007 (all adapter methods must exist)
  **Test needed**: Yes (T010 covers this)
  **Risk**: LOW

**Checkpoint**: `SkillsInvoker.run()` and `SkillsRegistry` complete.

---

## Phase 9: ⚠️ HIGH RISK — Prototype Wiring (process_ticket integration)

**Purpose**: Replace the direct module calls in `prototype.py::process_ticket` with `SkillsInvoker`. This is the highest-risk task — it touches the core loop that all 79 tests exercise.

**⚠️ HIGH RISK**: This task modifies `prototype.py::process_ticket`. If the wiring is wrong, all 79 tests can fail simultaneously.

**MANDATORY**: Run `python -m pytest tests/ -v` immediately after completing this task. All 79 tests must pass before committing.

- [ ] T009c ⚠️ **[HIGH RISK]** Update `src/agent/prototype.py::process_ticket` to delegate to `SkillsInvoker` — `src/agent/prototype.py`

  **File**: `src/agent/prototype.py` (modify existing)

  **Exact changes** (smallest viable diff):

  1. Add import at top of file:
     ```python
     from src.agent.skills_invoker import SkillsInvoker
     ```

  2. Add module-level invoker instance (alongside existing `_kb`):
     ```python
     _invoker = SkillsInvoker()
     ```

  3. In `process_ticket(msg)`, replace the block from line 148 ("Step 1b: Resolve identity") through the `_kb.search()` call and `evaluate_escalation()` call with:
     ```python
     # Step 1b–3: Run skills pipeline (Customer ID → Sentiment → KB → Escalation)
     inv_result = _invoker.run(msg)
     customer_key = inv_result.customer_id_result.customer_id
     escalation = _map_escalation(inv_result.escalation_result)
     kb_results = inv_result.kb_result.results if inv_result.kb_result else []
     ```

     Where `_map_escalation` is a private module-level function that converts `EscalationDecisionResult` back to the `EscalationDecision` namedtuple/dataclass that the rest of `process_ticket` already uses:
     ```python
     def _map_escalation(r: EscalationDecisionResult) -> EscalationDecision:
         return EscalationDecision(
             should_escalate=r.should_escalate,
             reason=r.reason or "",
             urgency=r.urgency,
         )
     ```

  4. Replace the `format_response(raw, ticket.channel, ticket.customer_first_name)` call with:
     ```python
     inv_result = _invoker.apply_channel_adaptation(
         inv_result, raw, ticket.channel.value, ticket.customer_first_name
     )
     formatted = inv_result.channel_result.formatted_response
     ```

  5. The `store.get_or_create_conversation`, `store.get_conversation_context`, `store.has_prior_topic`, `store.add_message`, `store.add_topic`, `store.transition_ticket` calls remain UNCHANGED — only the identity resolution, KB search, escalation evaluation, and formatting calls move into the invoker.

  **Acceptance criteria (ALL must pass before committing)**:
  - `python -m pytest tests/ -v` → all 79 tests pass (0 failures, 0 errors).
  - `python -c "from src.agent.prototype import process_ticket; print('OK')"` exits 0.
  - `process_ticket(TicketMessage(...))` returns an `AgentResponse` with a non-empty `response` field.

  **Dependencies**: T009a, T009b (registry + invoker.run() must be complete)
  **Test needed**: YES — run full pytest suite immediately after
  **Risk**: ⚠️ HIGH — modifies the core loop; any type mismatch between EscalationDecisionResult and EscalationDecision breaks all escalation tests

**Checkpoint**: ALL 79 EXISTING TESTS PASS. Only commit after pytest confirms this.

---

## Phase 10: Tests — Skills Registry + Invoker Orchestration

**Purpose**: Add explicit tests for the new skills layer so regressions are caught in future phases.

- [ ] T010 Create `tests/test_skills.py` — registry lookup + invoker orchestration order tests

  **File**: `tests/test_skills.py` (new file)

  **Test cases to include**:

  ```python
  # Registry tests
  def test_registry_returns_all_5_skills(): ...
  def test_registry_sorted_by_priority(): ...
  def test_registry_lookup_by_id(): ...
  def test_registry_raises_key_error_on_unknown_id(): ...

  # SkillManifest tests
  def test_skill_manifest_is_frozen(): ...
  def test_all_skills_have_guardrails(): ...

  # Invoker result dataclass tests
  def test_customer_identification_result_fields(): ...
  def test_invoker_result_channel_result_starts_none(): ...

  # _run_customer_identification
  def test_new_customer_creates_profile(): ...
  def test_returning_customer_detected(): ...

  # _run_sentiment_analysis
  def test_no_history_returns_insufficient_data(): ...
  def test_deteriorating_trend_sets_escalation_recommended(): ...

  # _run_knowledge_retrieval
  def test_empty_query_returns_empty_results(): ...
  def test_product_query_returns_results(): ...

  # _run_escalation_decision
  def test_threat_message_escalates(): ...
  def test_deteriorating_sentiment_triggers_escalation(): ...
  def test_benign_message_no_escalation(): ...

  # apply_channel_adaptation
  def test_raises_when_should_escalate_true(): ...
  def test_whatsapp_truncated_to_3_sentences(): ...

  # Full invoker pipeline order
  def test_run_returns_all_fields(): ...
  def test_channel_result_is_none_after_run(): ...
  def test_apply_channel_adaptation_populates_channel_result(): ...
  ```

  Use `ConversationStore()` (fresh instance, not `get_store()`) for test isolation. Use `reset_store()` in teardown if any test calls `get_store()`.

  **Acceptance criteria**:
  - `python -m pytest tests/test_skills.py -v` → all new tests pass.
  - `python -m pytest tests/ -v` → all 79 + new tests pass (no regressions).

  **Dependencies**: T009a, T009b, T009c (all skills + prototype wiring complete)
  **Test needed**: YES — this IS the test task
  **Risk**: LOW

---

## Phase 11: Polish

- [ ] T011 [P] Update `CLAUDE.md` Recent Changes entry to note Phase 2E implementation complete: `src/agent/skills_manifest.py`, `src/agent/skills_registry.py`, `src/agent/skills_invoker.py`

  **File**: `CLAUDE.md`
  **Dependencies**: T010
  **Test needed**: No
  **Risk**: LOW

---

## Dependencies & Execution Order

### Phase Dependencies

```
T001 (verify imports)
  └── T002 (skills_manifest.py) ← BLOCKS all below
        ├── T003 (result dataclasses + stubs) → T004 → T005 → T006 → T007 → T008
        │                                                                      │
        └── T009a (skills_registry.py) [P with T003]                          │
              └── T009b (invoker.run()) ← depends on T004..T008 complete ─────┘
                    └── T009c ⚠️ HIGH RISK (prototype.py wiring)
                          └── T010 (tests/test_skills.py)
                                └── T011 (CLAUDE.md update)
```

### Parallel Opportunities

- **T003 and T009a** can run in parallel (different files, both depend only on T002).
- **T004–T008** must run sequentially (each adds a method to skills_invoker.py).
- **T009a** (registry) and **T009b** (invoker.run) can start as soon as T002 and T004–T008 are done.

### User Story Independence

| User Story | Skill | Priority | Depends on |
|------------|-------|----------|------------|
| US5 — Customer Identification | customer_identification_v1 | P1 (priority 0) | T002, T003 |
| US2 — Sentiment Analysis | sentiment_analysis_v1 | P1 (priority 1) | US5 done |
| US1 — Knowledge Retrieval | knowledge_retrieval_v1 | P1 (priority 2) | US2 done |
| US3 — Escalation Decision | escalation_decision_v1 | P2 (priority 3) | US1 done |
| US4 — Channel Adaptation | channel_adaptation_v1 | P1 (priority 4) | US3 done |

---

## Task Summary

| Task | File | Risk | Test |
|------|------|------|------|
| T001 | — (verification) | LOW | No |
| T002 | src/agent/skills_manifest.py | LOW | Yes (T010) |
| T003 | src/agent/skills_invoker.py | LOW | Yes (T010) |
| T004 | src/agent/skills_invoker.py | LOW | Yes (T010) |
| T005 | src/agent/skills_invoker.py | LOW | Yes (T010) |
| T006 | src/agent/skills_invoker.py | LOW | Yes (T010) |
| T007 | src/agent/skills_invoker.py | LOW | Yes (T010) |
| T008 | src/agent/skills_invoker.py | LOW | Yes (T010) |
| T009a | src/agent/skills_registry.py | LOW | Yes (T010) |
| T009b | src/agent/skills_invoker.py | LOW | Yes (T010) |
| T009c | src/agent/prototype.py | ⚠️ HIGH | **Mandatory pytest after** |
| T010 | tests/test_skills.py | LOW | IS the test |
| T011 | CLAUDE.md | LOW | No |

**Total tasks: 13** (T001, T002, T003, T004, T005, T006, T007, T008, T009a, T009b, T009c, T010, T011)
**HIGH RISK: 1** (T009c — prototype.py wiring)

---

## Implementation Strategy

### MVP First (verify wiring before tests)

1. Complete T001 → T002 (foundational)
2. Complete T003 → T009b (build invoker without touching prototype)
3. Complete T009a (registry — safe, new file)
4. ⚠️ T009c (wire prototype — run pytest immediately)
5. Complete T010 (add skills-specific tests)

### Safety Protocol for T009c

Before starting T009c:
- Confirm `python -m pytest tests/ -v` shows 79 passes.
- Make one small change at a time; run pytest after each change.
- If any test fails, revert the change before proceeding.

---

## Notes

- `[P]` = different files, no dependency on each other — can run in parallel.
- Tasks T004–T008 each modify the same file (`skills_invoker.py`) — they must run sequentially.
- `[US1]`–`[US5]` map to the 5 user stories in `spec-2e-agent-skills.md`.
- T009c is the only task that modifies an existing file with 79 tests behind it — treat it as the highest-risk commit.
- Run `python -m pytest tests/ -v` after T009c before any other task.
