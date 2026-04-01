# Tasks: Phase 2B — Prototype Core Loop

**Feature**: `001-incubation-exploration`
**Branch**: `001-incubation-exploration`
**Date**: 2026-04-01
**Input**: `specs/001-incubation-exploration/plan.md` (9 tasks T1–T9)
**Risk flags**: T6 (escalation evaluator) = HIGH RISK | T8 (core loop) = HIGH RISK
**Test stubs**: Required for T6 and T8 — written BEFORE implementation

---

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Parallelizable — different files, no incomplete-task dependencies
- **[US1–US4]**: Maps to user story in `spec.md`
- File path is included in every task description

---

## Phase 1: Setup

**Purpose**: Declare dependencies, ensure import paths exist, configure `.env` handling.

- [ ] T001 Add `openai>=1.0`, `python-dotenv` to `requirements.txt`; create `src/__init__.py` and `src/agent/__init__.py`; add `OPENAI_API_KEY=sk-your-key-here` to `.env.example`

**Acceptance**: `python -c "import openai, dotenv; print('OK')"` passes after `pip install -r requirements.txt`. Both `__init__.py` files exist and are empty.

**Checkpoint**: Dependencies declared — prototype can now import `openai` and `dotenv`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data types and prompt infrastructure that EVERY subsequent task depends on.

⚠️ **CRITICAL**: No Phase 3–5 tasks can begin until this phase is complete.

- [ ] T002 Create all six typed dataclasses in `src/agent/models.py`: `Channel` (str Enum), `TicketMessage`, `NormalizedTicket`, `KBResult`, `EscalationDecision`, `AgentResponse` — exact field definitions from `specs/001-incubation-exploration/data-model.md`
- [ ] T003 [P] Create `src/agent/prompts.py` with `get_system_prompt(channel: str, customer_name: str) -> str` that injects `datetime.now(ZoneInfo("Asia/Karachi"))` — no hardcoded dates, no `datetime.utcnow()`

**Acceptance (T002)**: All six classes importable; `repr()` works on a hand-constructed instance of each; zero external dependencies (stdlib only + `from __future__ import annotations`).

**Acceptance (T003)**: `get_system_prompt("email", "Sarah")` output contains the current date string. Calling it twice 1 second apart produces the same minute but proves live injection (not cached).

**Checkpoint**: Foundation ready — all typing and prompt infrastructure exists.

---

## Phase 3: User Story 1 — Ticket Pattern Discovery (Priority: P1) 🎯 MVP Core

**Goal**: Implement the three channel-aware components that form the resolution path — message normalization, KB search, and channel-specific formatting. US1 proves the agent understands channel differences.

**Independent Test**: Process TKT-002 (email) — response starts with "Dear James," and ends with the NexaFlow signature. Process TKT-025 (WhatsApp) — response starts with "Hi Marcus! 👋" and is ≤ 1600 chars.

- [ ] T004 [US1] Add `normalize_message(msg: TicketMessage) -> NormalizedTicket` to `src/agent/prototype.py` — implement all three channel branches (email, whatsapp, web_form) per `data-model.md` normalization rules including language detection
- [ ] T005 [P] [US1] Create `src/agent/knowledge_base.py` with `KnowledgeBase` class: load `context/product-docs.md`, split by `##` headers, score by Jaccard word-overlap, return top-3 `KBResult` objects sorted by `relevance_score` descending
- [ ] T006 [P] [US1] Create `src/agent/channel_formatter.py` with `format_response(raw: str, channel: Channel, name: str) -> str` — implement email (≤2500 chars, "Dear [Name],", NexaFlow signature), WhatsApp (≤1600 hard / 300 soft, "Hi [Name]! 👋", truncate + "…"), web_form ("Hi [Name],", ≤5000 chars) per `plan.md` T5 rules

**Acceptance (T004)**:
- WhatsApp ticket with `subject=None` → `inferred_topic` = first 10 words of message; `identifier_type="phone"` when email is null
- Email ticket → `identifier_type="email"`; `inferred_topic = subject`
- `channel` in `NormalizedTicket` always equals source `TicketMessage.channel`

**Acceptance (T005)**:
- Query "Slack integration authentication failed" → Slack section is top result with `relevance_score > 0`
- Query "xyznonexistentterm999" → empty list OR all results `relevance_score < 0.05`
- Loads from both absolute and relative paths without error

**Acceptance (T006)**:
- `format_response(text, Channel.WHATSAPP, "Marcus")` returns string ≤ 1600 chars starting with "Hi Marcus! 👋"
- `format_response(text, Channel.EMAIL, "James")` starts with "Dear James," and ends with NexaFlow signature block
- `format_response(text, Channel.WEB_FORM, "Alice")` starts with "Hi Alice,"

**Checkpoint**: All three channel-aware components work independently — US1 deliverable.

---

## Phase 4: User Story 3 — Edge Case Catalogue (Priority: P1) ⚠️ HIGH RISK × 2

**Goal**: Implement LLM-intent escalation detection and the integrated core loop. T007 and T009 are test stubs — write them FIRST, verify they fail, then implement T008 and T010.

**Independent Test**: TKT-006 (furious customer + human request) → `should_escalate=True`. TKT-003 (billing question with "charged") → `should_escalate=False` (no false positive). TKT-044 (GDPR) → `should_escalate=True, urgency="normal"`.

### ⚠️ HIGH RISK — Test Stubs First

- [ ] T007 [P] [US3] Write test stub `tests/test_escalation_evaluator.py` with three failing assertions: (1) TKT-006 input → `should_escalate=True` and reason mentions sentiment or human-request, (2) TKT-003 input → `should_escalate=False`, (3) TKT-044 input → `should_escalate=True` and reason mentions legal/compliance; also assert `json.loads(result.raw_llm_response)` succeeds — stubs must FAIL before T008

- [ ] T009 [P] [US3] Write test stub `tests/test_core_loop.py` with four failing assertions: (1) `process_ticket(tkt_002_email)` returns `AgentResponse` without exception, (2) escalation is evaluated before `generate_response` (verify via `escalation` field always populated), (3) TKT-006 → `should_escalate=True` (short-circuit, no LLM response generated), (4) TKT-025 → `formatted_response` length ≤ 1600 chars — stubs must FAIL before T010

### Implementation (write AFTER test stubs are confirmed failing)

- [ ] T008 [US3] ⚠️ HIGH RISK — Create `src/agent/escalation_evaluator.py` with `evaluate_escalation(message: str) -> EscalationDecision`: call `gpt-4o-mini` with structured JSON system prompt describing the 8 escalation triggers from constitution §V (sentiment < 0.3, refund, legal/GDPR, pricing negotiation, 3+ follow-ups, explicit human request, data breach, Enterprise SLA breach) — NO keyword lists, describe intent conceptually; parse JSON response into `EscalationDecision`; store raw LLM JSON in `raw_llm_response`

- [ ] T010 [US3] ⚠️ HIGH RISK — Complete `src/agent/prototype.py` `process_ticket(msg: TicketMessage) -> AgentResponse` following the strict 6-step flow from `plan.md` T8: (1) `create_ticket` → in-memory ticket_id + `normalize_message`, (2) empty customer history, (3) `search_knowledge_base`, (4) `evaluate_escalation`, (5) IF escalated → return escalation acknowledgment template without calling OpenAI main, (6) ELSE → `generate_response` via `gpt-4o` + `format_response` → return `AgentResponse` with all fields populated including `processing_time_ms` and `prompt_datetime`

**Acceptance (T008)**:
- TKT-006 text → `should_escalate=True`; reason mentions sentiment/human-request
- TKT-003 text ("prorated charge question") → `should_escalate=False` (LLM intent beats keyword match)
- TKT-044 GDPR text → `should_escalate=True`; reason mentions legal/compliance
- `json.loads(result.raw_llm_response)` succeeds without exception

**Acceptance (T010)**:
- `process_ticket()` returns `AgentResponse` for all 3 channel types without raising
- `AgentResponse.escalation` is never null
- `AgentResponse.formatted_response` is never null or empty
- Escalated tickets → `kb_results_used == []` (no KB search on escalation path)
- `processing_time_ms > 0` and `prompt_datetime` contains the PKT string

**Checkpoint**: Core loop complete — edge case handling proven via T007/T009 test stubs passing.

---

## Phase 5: User Story 4 — Requirement Extraction Verification (Priority: P2)

**Goal**: Wire the CLI entry point and run the prototype against the 5 Phase-2A representative tickets to prove all 14 discovered requirements are met in the implementation.

**Independent Test**: `python src/agent/prototype.py` runs all 5 test tickets without exception. TKT-006 and TKT-044 print `Escalated: True`. TKT-025 prints `Response length: ≤ 1600 chars`.

- [ ] T011 [US4] Add `if __name__ == "__main__":` block to `src/agent/prototype.py` and write `tests/test_prototype.py` loading test fixtures from `context/sample-tickets.json` for TKT-002 (email, neutral), TKT-006 (email, furious + human request), TKT-025 (WhatsApp, short), TKT-032 (WhatsApp, gibberish), TKT-044 (web_form, GDPR); assert all 5 produce `AgentResponse`; assert TKT-006 and TKT-044 `should_escalate=True`; assert TKT-025 `len(formatted_response) <= 1600`; assert TKT-002 and TKT-025 `should_escalate=False`

**Acceptance (T011)**:
- All 5 tickets produce `AgentResponse` without raising exceptions
- TKT-006 and TKT-044: `escalation.should_escalate=True`
- TKT-002, TKT-025, TKT-032: `escalation.should_escalate=False`
- TKT-025: `len(formatted_response) <= 1600`
- Total run time for all 5 tickets < 60s (prototype, not production target)

**Checkpoint**: All user stories validated — prototype is demo-ready.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T012 [P] Validate `quickstart.md` end-to-end: run all 5 steps from `specs/001-incubation-exploration/quickstart.md`; confirm output matches expected format; update quickstart if any step diverges from actual implementation

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup)
    │
    ▼
Phase 2 (Foundational) — BLOCKS all story phases
    │
    ├──► Phase 3 (US1 — components) — T004, T005, T006 can run in parallel
    │
    ├──► Phase 4 (US3 — HIGH RISK) — T007 and T009 (test stubs) first; then T008, T010
    │
    └──► Phase 5 (US4 — verification) — requires Phase 3 + Phase 4 complete
             │
             ▼
         Phase 6 (Polish)
```

### Task-Level Dependencies

| Task | Depends On | Parallelizable With |
|------|-----------|---------------------|
| T001 | — | — |
| T002 | T001 | — |
| T003 | T001 | T002 |
| T004 | T002, T003 | — |
| T005 | T002 | T004, T006 |
| T006 | T002 | T004, T005 |
| T007 | T002, T003 | T009 |
| T008 | T007 (stub must fail first) | — |
| T009 | T002, T003, T004, T005, T006 | T007 |
| T010 | T008, T009 (stub must fail first) | — |
| T011 | T010 | — |
| T012 | T011 | — |

### Parallel Opportunities

```bash
# Phase 2 (after T001):
T002 [data models]  ||  T003 [prompts]

# Phase 3 (after T002 + T003):
T004 [normalization]  ||  T005 [KB search]  ||  T006 [channel formatter]

# Phase 4 test stubs (after Phase 2 complete):
T007 [escalation test stub]  ||  T009 [core loop test stub]
```

---

## Implementation Strategy

### MVP First (Phase 1–3)

1. Complete **Phase 1**: Setup
2. Complete **Phase 2**: Foundational (data models + prompts)
3. Complete **Phase 3**: US1 components (normalization, KB, formatter)
4. **STOP and VALIDATE**: Each US1 component works independently

### HIGH RISK Tasks (Phase 4)

1. Write **T007** (escalation test stub) — confirm it FAILS
2. Write **T009** (core loop test stub) — confirm it FAILS
3. Implement **T008** (escalation evaluator) — confirm T007 now PASSES
4. Implement **T010** (core loop) — confirm T009 now PASSES
5. **STOP and VALIDATE**: TKT-006 escalates, TKT-003 does NOT escalate

### Final Verification (Phase 5–6)

1. Complete **T011** (CLI + test_prototype.py)
2. Run all 5 test tickets — confirm expected outputs
3. Complete **T012** (quickstart validation)

---

## Notes

- `[P]` tasks touch different files with no blocking dependencies — run in parallel to save time
- Test stubs for T007 and T009 MUST fail before T008/T010 are implemented (TDD for high-risk tasks)
- Never use keyword matching for escalation — LLM intent only (per constitution §V and R11)
- Every `get_system_prompt()` call MUST use `datetime.now(ZoneInfo("Asia/Karachi"))` — no hardcoded dates
- `prototype.py` is the single entry point file for T004 (normalization) + T010 (core loop) + T011 (CLI)
- Commit after each phase checkpoint — no giant commits spanning multiple phases
