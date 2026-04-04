# Tasks: MCP Server — CRM Tool Gateway

**Feature**: `003-mcp-server` | **Phase**: 2D | **Branch**: `003-mcp-server`  
**Input**: `specs/003-mcp-server/plan.md`, `specs/003-mcp-server/spec.md`,
`specs/003-mcp-server/contracts/tool_schemas.md`, `specs/003-mcp-server/data-model.md`

---

## Context7 API Lookup Notes (pre-task research)

Patterns confirmed from `specs/003-mcp-server/research.md` (source: modelcontextprotocol.io):

1. **`@mcp.tool()` decorator** — `from mcp.server.fastmcp import FastMCP`; `mcp = FastMCP("name")`;
   `@mcp.tool() async def my_tool(param: str) -> str: ...` — auto-generates JSON schema from
   type hints + docstrings; the decorated function remains a directly callable coroutine.
2. **`mcp.run()` signature** — `mcp.run(transport="stdio")` inside `def main()`; entry point via
   `if __name__ == "__main__": main()`. No port is allocated.
3. **Error handling contract** — All tools return `str`. Errors: `json.dumps({"error": "...", "tool": "tool_name"})`.
   Validation errors returned **before** the try/except block. NEVER raise out of a tool function.

---

## Format: `[ID] [P?] [Story?] Description with file path`

- **[P]**: Can run in parallel (independent files / no blocking dependency)
- **[Story]**: User story label — required for Phase 3+ tasks (US1–US7)
- **⚠️ HIGH RISK**: Extra care required — see risk note inline

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add the `mcp` dependency and create package skeletons so all imports resolve.

- [X] T001 Add `mcp>=1.2.0` to `requirements.txt` and verify `pip install -r requirements.txt` succeeds without conflict
- [X] T002 [P] Create `src/mcp_server/__init__.py` as an empty package marker file
- [X] T003 [P] Create `tests/unit/mcp_server/__init__.py` as an empty package marker file

**Acceptance Criteria**:
- `requirements.txt` contains `mcp>=1.2.0` line
- `pip install -r requirements.txt` exits 0
- Both `__init__.py` files exist (empty or containing `# Phase 2D`)
- `python -c "from mcp.server.fastmcp import FastMCP"` exits 0

**Checkpoint**: Package can be imported — proceed to server scaffold.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create the server skeleton that all 7 tool implementations will be added to.
No tool logic yet — only scaffold, imports, logging setup, `_ticket_index`, and `main()`.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T004 Create `src/mcp_server/server.py` with FastMCP scaffold — imports (`json`, `sys`, `uuid`, `logging`, `datetime`, `FastMCP`, `KnowledgeBase`, `get_store`, `TicketStatus`, `Channel`), `_kb = KnowledgeBase()`, `store = get_store()`, `_ticket_index: dict[str, str] = {}`, `mcp = FastMCP("nexaflow-crm")`, `logging.basicConfig(level=logging.INFO, stream=sys.stderr)`, `def main(): mcp.run(transport="stdio")`, `if __name__ == "__main__": main()` — NO tool implementations yet ⚠️ **HIGH RISK** (stdout must stay clean; any `print()` corrupts JSON-RPC)

- [X] T005 Create `tests/unit/mcp_server/test_tools.py` with: import of `asyncio`, `json`, `pytest`; import all 7 tool function names from `src.mcp_server.server`; `@pytest.fixture(autouse=True)` that calls `reset_store()` from `src.agent.conversation_store`; one smoke-import test `test_server_imports_without_error` that asserts all 7 names are callable

**Acceptance Criteria**:
- `python -m src.mcp_server.server` starts without error (Ctrl+C to exit)
- `from src.mcp_server.server import search_knowledge_base` resolves in Python REPL
- `pytest tests/unit/mcp_server/test_tools.py::test_server_imports_without_error -v` passes
- No `print()` statements anywhere in `server.py`

**Checkpoint**: Foundation ready — user story implementation can now begin.

---

## Phase 3: User Story 1 — AI Agent Searches Knowledge Base (Priority: P1) 🎯 MVP

**Goal**: Expose `search_knowledge_base` — the underpinning of every ticket response.

**Independent Test**: `pytest tests/unit/mcp_server/test_tools.py -k "search" -v` passes.

### Tests for User Story 1

> **Write these tests FIRST — they must FAIL before T007 is implemented.**

- [X] T006 [US1] Add 3 test functions to `tests/unit/mcp_server/test_tools.py`:
  `test_search_returns_ranked_results` (valid query → `results` list non-empty, each item has `section_title`, `content`, `relevance_score`),
  `test_search_no_match_returns_empty` (nonsense query → `{"results": [], "count": 0}`),
  `test_search_empty_query_returns_validation_error` (empty string → JSON with `"error"` key containing `"validation"`)

### Implementation for User Story 1

- [X] T007 [US1] Implement `search_knowledge_base(query: str) -> str` tool in `src/mcp_server/server.py` — validate `query` non-empty (return validation error JSON if empty); call `_kb.search(query, top_k=3)`; serialise results to `{"results": [...], "count": N, "query": "..."}` per `contracts/tool_schemas.md`; wrap in `try/except Exception as e` returning `json.dumps({"error": str(e), "tool": "search_knowledge_base"})`

**Acceptance Criteria**:
- All 3 US1 tests pass: `pytest tests/unit/mcp_server/test_tools.py -k "search" -v`
- Empty query returns `{"error": "validation: query must not be empty", "tool": "search_knowledge_base"}`
- Valid query returns `{"results": [...], "count": N, "query": "..."}` (count may be 0 for no match)
- No exception propagates out of the tool function

**Checkpoint**: US1 independently functional and tested.

---

## Phase 4: User Story 2 — AI Agent Creates a Support Ticket (Priority: P1)

**Goal**: Expose `create_ticket` — the entry point for every customer interaction. Populates `_ticket_index`.

**Independent Test**: `pytest tests/unit/mcp_server/test_tools.py -k "create_ticket" -v` passes.

### Tests for User Story 2

> **Write these tests FIRST — they must FAIL before T009 is implemented.**

- [X] T008 [US2] Add 5 test functions to `tests/unit/mcp_server/test_tools.py`:
  `test_create_ticket_returns_id` (valid inputs → response contains `ticket_id` starting with `"TKT-"`),
  `test_create_ticket_new_customer` (unknown customer_id → ticket still created, customer profile created),
  `test_create_ticket_invalid_channel` (channel=`"fax"` → JSON error containing `"validation"`),
  `test_create_ticket_invalid_priority` (priority=`"urgent"` → JSON error containing `"validation"`),
  `test_create_ticket_empty_issue` (issue=`""` → JSON error containing `"validation"`)

### Implementation for User Story 2 ⚠️ HIGH RISK

- [X] T009 [US2] Implement `create_ticket(customer_id: str, issue: str, priority: str, channel: str) -> str` tool in `src/mcp_server/server.py` ⚠️ **HIGH RISK** (_ticket_index population is critical for all subsequent ticket-scoped tools) — before try block: validate `priority` in `{"low","medium","high","critical"}` (error if not); validate `channel` in `{"email","whatsapp","web_form"}` (error if not); validate `issue` non-empty (error if empty); validate `customer_id` non-empty (error if empty); inside try: call `store.get_or_create_customer(key=customer_id, name=customer_id, channel=channel)`, `store.get_or_create_conversation(customer_key=customer_id, channel=channel)`, `store.add_topic(conv.id, issue[:100])`; generate `ticket_id = conv.ticket.id`; register `_ticket_index[ticket_id] = conv.id`; return `json.dumps({"ticket_id": ticket_id, "customer_id": customer_id, "status": "open", "channel": channel, "created_at": conv.ticket.opened_at})`

**Acceptance Criteria**:
- All 5 US2 tests pass: `pytest tests/unit/mcp_server/test_tools.py -k "create_ticket" -v`
- Returned `ticket_id` is resolvable: `_ticket_index[ticket_id]` returns a valid UUID
- Invalid channel returns `{"error": "validation: channel must be one of: email, whatsapp, web_form", "tool": "create_ticket"}`
- Invalid priority returns `{"error": "validation: priority must be one of: low, medium, high, critical", "tool": "create_ticket"}`

**Checkpoint**: US2 independently functional; `_ticket_index` populated — US4, US5, US7 can now be implemented.

---

## Phase 5: User Story 5 — AI Agent Sends a Response to the Customer (Priority: P1)

**Goal**: Expose `send_response` — the agent's core delivery action.

**Independent Test**: `pytest tests/unit/mcp_server/test_tools.py -k "send_response" -v` passes.

### Tests for User Story 5

> **Write these tests FIRST — they must FAIL before T011 is implemented.**

- [X] T010 [US5] Add 4 test functions to `tests/unit/mcp_server/test_tools.py`:
  `test_send_response_success` (create ticket first, then call send_response with valid channel → response contains `delivery_status == "delivered"`, `channel`, `timestamp`),
  `test_send_response_invalid_channel` (channel=`"sms"` → JSON error containing `"validation"`),
  `test_send_response_empty_message` (message=`""` → JSON error containing `"validation"`),
  `test_send_response_unknown_ticket` (ticket_id=`"TKT-notreal"` → JSON error containing `"not found"`)

### Implementation for User Story 5

- [X] T011 [US5] Implement `send_response(ticket_id: str, message: str, channel: str) -> str` tool in `src/mcp_server/server.py` — before try: validate `channel` in `{"email","whatsapp","web_form"}` (validation error if not); validate `message` non-empty (validation error if empty); inside try: lookup `conv_id = _ticket_index.get(ticket_id)`, if missing return not-found JSON; call `store.add_message(conv_id, message_obj)` where `message_obj` is a simulated outbound `Message`; log to stderr: `logging.info("[SIMULATED SEND] channel=%s ticket=%s len=%d", channel, ticket_id, len(message))`; return `json.dumps({"delivery_status":"delivered","ticket_id":ticket_id,"channel":channel,"message_length":len(message),"timestamp":"<utc_iso>"})`

**Acceptance Criteria**:
- All 4 US5 tests pass: `pytest tests/unit/mcp_server/test_tools.py -k "send_response" -v`
- No `print()` used — simulated delivery logged to stderr only
- Unknown ticket returns `{"error": "ticket TKT-... not found", "tool": "send_response"}`

**Checkpoint**: All P1 stories (US1, US2, US5) complete and independently tested.

---

## Phase 6: User Story 3 — AI Agent Retrieves Full Customer History (Priority: P2)

**Goal**: Expose `get_customer_history` — cross-channel context awareness from Phase 2C memory.

**Independent Test**: `pytest tests/unit/mcp_server/test_tools.py -k "history" -v` passes.

### Tests for User Story 3

> **Write these tests FIRST — they must FAIL before T013 is implemented.**

- [X] T012 [US3] Add 3 test functions to `tests/unit/mcp_server/test_tools.py`:
  `test_history_multichannel` (create 2 tickets across different channels for same customer → history response includes both channels in `channels_used`, `conversation_count == 2`),
  `test_history_unknown_customer` (unknown customer_id → `{"conversation_count": 0, "conversations": []}`, no error key),
  `test_history_empty_customer_id` (customer_id=`""` → JSON error containing `"validation"`)

### Implementation for User Story 3

- [X] T013 [US3] Implement `get_customer_history(customer_id: str) -> str` tool in `src/mcp_server/server.py` — before try: validate `customer_id` non-empty (validation error if empty); inside try: call `store.get_customer(customer_id)`, if None return empty history JSON `{"customer_id":..., "name":null, "channels_used":[], "conversation_count":0, "conversations":[]}`; iterate `profile.conversation_ids`, for each `conv_id` fetch `store._conversations[conv_id]` and build conversation summary dict; return `json.dumps({"customer_id":..., "name":..., "channels_used":list(profile.channels_used), "conversation_count":..., "conversations":[...]})` per `data-model.md`

**Acceptance Criteria**:
- All 3 US3 tests pass: `pytest tests/unit/mcp_server/test_tools.py -k "history" -v`
- Unknown customer returns empty history object, not an error
- Multi-channel history includes all channels in `channels_used`

**Checkpoint**: US3 independently functional.

---

## Phase 7: User Story 4 — AI Agent Escalates a Ticket to Human (Priority: P2) ⚠️ HIGH RISK

**Goal**: Expose `escalate_to_human` — the safety valve for AI handoffs. HIGH RISK due to state
transitions and optional OpenAI dependency.

**Independent Test**: `pytest tests/unit/mcp_server/test_tools.py -k "escalate" -v` passes.

### Tests for User Story 4

> **Write these tests FIRST — they must FAIL before T015 is implemented.**

- [X] T014 [US4] Add 3 test functions to `tests/unit/mcp_server/test_tools.py`:
  `test_escalate_success` (create ticket, then escalate → response contains `escalation_id` starting with `"ESC-"`, `status == "escalated"`),
  `test_escalate_unknown_ticket` (ticket_id not in `_ticket_index` → JSON error containing `"not found"`),
  `test_escalate_already_escalated` (create ticket, escalate once, escalate again → returns JSON error containing `"invalid transition"` or idempotent response — NOT an unhandled exception)

### Implementation for User Story 4

- [X] T015 [US4] Implement `escalate_to_human(ticket_id: str, reason: str) -> str` tool in `src/mcp_server/server.py` ⚠️ **HIGH RISK** (state transition validation + OpenAI fallback) — before try: validate `reason` non-empty (validation error if empty); validate `ticket_id` non-empty (validation error if empty); inside try: lookup `conv_id = _ticket_index.get(ticket_id)`, if missing return not-found JSON; call `store.transition_ticket(conv_id, TicketStatus.ESCALATED)` — catch `ValueError` from invalid transitions and return as JSON error; generate `escalation_id = "ESC-" + uuid.uuid4().hex[:8]`; check `os.getenv("OPENAI_API_KEY")` — if absent, skip evaluator call and escalate unconditionally (log warning to stderr); return `json.dumps({"escalation_id":..., "ticket_id":..., "status":"escalated", "reason":reason, "escalated_at":"<utc_iso>"})`

**Acceptance Criteria**:
- All 3 US4 tests pass: `pytest tests/unit/mcp_server/test_tools.py -k "escalate" -v`
- Returned `escalation_id` matches pattern `ESC-[a-f0-9]{8}`
- Already-escalated ticket returns descriptive JSON error, not an unhandled exception
- Server boots and `escalate_to_human` returns a result even when `OPENAI_API_KEY` is unset

**Checkpoint**: US4 independently functional.

---

## Phase 8: User Story 7 — AI Agent Resolves a Ticket (Priority: P2) ⚠️ HIGH RISK

**Goal**: Expose `resolve_ticket` — ticket lifecycle closure. HIGH RISK due to idempotency contract.

**Independent Test**: `pytest tests/unit/mcp_server/test_tools.py -k "resolve" -v` passes.

### Tests for User Story 7

> **Write these tests FIRST — they must FAIL before T017 is implemented.**

- [X] T016 [US7] Add 4 test functions to `tests/unit/mcp_server/test_tools.py`:
  `test_resolve_success` (create ticket, call resolve_ticket with non-empty summary → `status == "resolved"`, `resolution_summary` in response),
  `test_resolve_already_resolved_idempotent` (create ticket, resolve, resolve again → second call returns JSON with `status == "resolved"` and `"note"` field, NOT an exception),
  `test_resolve_empty_summary` (resolution_summary=`""` → JSON error containing `"validation"`),
  `test_resolve_unknown_ticket` (ticket_id=`"TKT-ghost"` → JSON error containing `"not found"`)

### Implementation for User Story 7

- [X] T017 [US7] Implement `resolve_ticket(ticket_id: str, resolution_summary: str) -> str` tool in `src/mcp_server/server.py` ⚠️ **HIGH RISK** (idempotency logic must handle already-RESOLVED terminal state) — before try: validate `resolution_summary` non-empty (validation error if empty); validate `ticket_id` non-empty (validation error if empty); inside try: lookup `conv_id = _ticket_index.get(ticket_id)`, if missing return not-found JSON; fetch `conv = store._conversations[conv_id]`; if `conv.ticket.status == TicketStatus.RESOLVED` return idempotent JSON `{"ticket_id":..., "status":"resolved", "note":"ticket was already resolved", "resolved_at":conv.ticket.closed_at}`; else call `store.transition_ticket(conv_id, TicketStatus.RESOLVED)` (catch `ValueError` for invalid transitions); call `store.add_topic(conv_id, f"resolved:{resolution_summary[:100]}")`; return `json.dumps({"ticket_id":..., "status":"resolved", "resolution_summary":resolution_summary, "resolved_at":"<utc_iso>"})`

**Acceptance Criteria**:
- All 4 US7 tests pass: `pytest tests/unit/mcp_server/test_tools.py -k "resolve" -v`
- Second resolve call returns idempotent JSON (note field present), no exception
- Empty summary returns `{"error": "validation: resolution_summary must not be empty", "tool": "resolve_ticket"}`

**Checkpoint**: All P2 stories (US3, US4, US7) complete and independently tested.

---

## Phase 9: User Story 6 — AI Agent Checks Customer Sentiment Trend (Priority: P3)

**Goal**: Expose `get_sentiment_trend` — proactive escalation signal from Phase 2C analytics.

**Independent Test**: `pytest tests/unit/mcp_server/test_tools.py -k "sentiment" -v` passes.

### Tests for User Story 6

> **Write these tests FIRST — they must FAIL before T019 is implemented.**

- [X] T018 [US6] Add 3 test functions to `tests/unit/mcp_server/test_tools.py`:
  `test_sentiment_insufficient_data` (create ticket with <3 inbound messages → response `trend == "stable"` and `"note": "insufficient data"`),
  `test_sentiment_unknown_customer` (unknown customer_id → response with `trend == "stable"`, `window_scores == []`, `recommend_escalation == false`),
  `test_sentiment_empty_customer_id` (customer_id=`""` → JSON error containing `"validation"`)

### Implementation for User Story 6

- [X] T019 [US6] Implement `get_sentiment_trend(customer_id: str) -> str` tool in `src/mcp_server/server.py` — before try: validate `customer_id` non-empty (validation error if empty); inside try: call `store.get_customer(customer_id)`, if None return stable empty trend JSON `{"customer_id":..., "trend":"stable", "window_scores":[], "window_size":3, "recommend_escalation":false, "note":"no history found"}`; get active or most recent conversation from `profile.conversation_ids`; call `store.compute_sentiment_trend(conv)` to get `SentimentTrend` result; map trend fields to JSON response `{"customer_id":..., "trend":trend.label, "window_scores":trend.window_scores, "window_size":3, "recommend_escalation":trend.label == "deteriorating"}`; add `"note": "insufficient data"` key if fewer than 3 data points

**Acceptance Criteria**:
- All 3 US6 tests pass: `pytest tests/unit/mcp_server/test_tools.py -k "sentiment" -v`
- `recommend_escalation` is `true` only when `trend == "deteriorating"`
- Unknown customer returns stable empty trend (not an error)

**Checkpoint**: All user stories (US1–US7) independently functional.

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Integration validation, regression gate, and registration.

- [X] T020 Add cross-tool integration test `test_fresh_store_all_tools_no_crash` to `tests/unit/mcp_server/test_tools.py` — on a fresh empty store (autouse fixture handles reset), call all 7 tools with valid-format inputs and assert each returns a valid JSON string (no exception propagates, no Python object returned)

- [X] T021 Run full regression suite `pytest -v` from project root — confirm all 52 pre-existing tests AND all new MCP server tests pass (SC-006: no existing tests may be broken)

- [X] T022 [P] Create or update `.claude.json` at project root with `mcpServers.nexaflow-crm` entry per `specs/003-mcp-server/quickstart.md` — command `python`, args `["-m", "src.mcp_server.server"]`, cwd `/home/ps_qasim/projects/crm-digital-fte`

- [X] T023 Integration smoke test — run `echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | python -m src.mcp_server.server` and confirm output contains all 7 tool names: `search_knowledge_base`, `create_ticket`, `get_customer_history`, `escalate_to_human`, `send_response`, `get_sentiment_trend`, `resolve_ticket` (SC-001)

**Acceptance Criteria**:
- `pytest -v` exits 0 with ≥52 + new MCP tests all green
- `.claude.json` contains correct `nexaflow-crm` server entry
- Smoke test JSON response contains all 7 tool names
- Server startup completes in <3 s (SC-005)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Requires Phase 1 completion (T001 before T004 for `mcp` import)
- **User Stories (Phase 3–9)**: All require Phase 2 completion (T004, T005 must exist)
  - US4, US5, US7 additionally require Phase 4 (T009 — `_ticket_index` must be populated)
  - US1, US2, US3, US6 have no inter-story dependencies
- **Polish (Phase 10)**: Requires all desired user stories complete

### Story Dependencies

- **US1 (P1)**: Depends on Foundational only
- **US2 (P1)**: Depends on Foundational only — **provides `_ticket_index` for US4/US5/US7**
- **US5 (P1)**: Depends on US2 completion (needs `_ticket_index` populated in tests)
- **US3 (P2)**: Depends on US2 (test helper creates tickets to build history)
- **US4 (P2)**: Depends on US2 completion (needs `_ticket_index`)
- **US7 (P2)**: Depends on US2 completion (needs `_ticket_index`)
- **US6 (P3)**: Depends on US2 (test helper creates tickets to build conversation history)

### Within Each Story

- Tests written FIRST (must FAIL) → Implementation → Tests PASS → Next story

---

## Parallel Opportunities

### Phase 1 (Setup)

```bash
# T002 and T003 can run in parallel (different directories)
Task T002: create src/mcp_server/__init__.py
Task T003: create tests/unit/mcp_server/__init__.py
```

### Phase 3–9 (after T009 establishes _ticket_index)

Once US2 (T009) is complete, these stories are independent of each other:
```bash
# With multiple developers — after T009:
Dev A: US3 (T012 → T013)  — get_customer_history
Dev B: US4 (T014 → T015)  — escalate_to_human
Dev C: US7 (T016 → T017)  — resolve_ticket
Dev D: US6 (T018 → T019)  — get_sentiment_trend
```

---

## HIGH RISK Task Summary

| Task | Risk | Mitigation |
|------|------|-----------|
| T004 | `print()` in server.py corrupts JSON-RPC stdout | Use `logging` to stderr; grep for `print(` before commit |
| T009 | `_ticket_index` not populated → US4/US5/US7 silently broken | Test verifies `_ticket_index[ticket_id]` exists after create_ticket |
| T015 | Invalid state transitions raise `ValueError` uncaught | Wrap in explicit `except ValueError`; test already-escalated scenario |
| T017 | Idempotent resolve: terminal state must not raise | Check `conv.ticket.status == RESOLVED` before transition; test covers this |

---

## Implementation Strategy

### MVP First (P1 Stories: US1 + US2 + US5)

1. Complete Phase 1: Setup (T001–T003)
2. Complete Phase 2: Foundational (T004–T005)
3. Complete Phase 3: US1 — search_knowledge_base (T006–T007)
4. Complete Phase 4: US2 — create_ticket (T008–T009) ← unlocks US4/US5/US7
5. Complete Phase 5: US5 — send_response (T010–T011)
6. **STOP and VALIDATE**: `pytest tests/unit/mcp_server/ -v` — all P1 tests green
7. Three hackathon-required tools are live

### Incremental Delivery

1. MVP done (P1) → add US3 → add US4 → add US7 → add US6
2. Each story adds one tool and its tests; no story breaks previous stories
3. After all 7 tools: polish phase (T020–T023)

---

## Notes

- `[P]` tasks create different files or have zero dependencies on incomplete tasks
- Tests use direct coroutine import: `result = asyncio.run(tool_function(arg))` — no MCP client
- `reset_store()` autouse fixture ensures hermetic isolation between every test
- Never add `print()` to `server.py` — use `logging.info/warning/error(...)`
- `store._conversations` is accessed directly (internal attribute) — document with comment
- All 52 pre-existing tests must remain green throughout (SC-006 invariant)
