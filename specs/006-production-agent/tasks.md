# Tasks: Production Agent — Phase 4B

**Input**: `specs/006-production-agent/`
**Branch**: `006-production-agent`
**Plan**: `specs/006-production-agent/plan.md`
**Spec**: `specs/006-production-agent/spec.md`
**Contracts**: `specs/006-production-agent/contracts/tools.md`
**Phase 4A baseline**: `production/database/queries.py` (complete; 101/101 tests passing)

> **Legend**
> - `⚠️ HIGH RISK` — async pool / LLM wiring; run `pytest` after each sub-step; must not break 101 existing tests
> - `[P]` — parallelisable (different files, no incomplete dependencies)
> - `[US1/2/3]` — maps to User Story from spec.md
> - **Recommended implementation order**: T001 → T002 → T003 → T004 → T005–T014 → T015–T018 → T019 → T020–T023 → T024–T029

---

## Phase 1: Setup

No new setup required — `production/` is scaffolded; Phase 4A is merged to main.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Pure-Python building blocks with no external I/O. Zero DB calls, zero OpenAI calls.
Must be complete before any tool or agent work begins.

**⚠️ CRITICAL**: No Phase 3/4/5 work until this phase is complete.

- [ ] T001 Create `production/agent/schemas.py` — 5 Pydantic v2 input models (plan T-001)
  - **File**: `production/agent/schemas.py` (NEW)
  - **Acceptance**:
    - `SearchKBInput(query: str max_length=500 min_length=1, limit: int=5 ge=1 le=20)`
    - `CreateTicketInput(customer_id: str, conversation_id: str, channel: str, subject: str|None=None, category: str|None=None)` — all fields have `Field(description=...)`
    - `EscalateInput(ticket_id: str, reason: str min_length=1, urgency: str="medium")`
    - `SendResponseInput(ticket_id: str, message: str min_length=1, channel: str)` — `ticket_id` Field description: `"UUID from create_ticket — call create_ticket first"`
    - `ResolveTicketInput(ticket_id: str, resolution_summary: str min_length=1)`
    - All 5 pass `ModelClass.model_json_schema()` without error (Pydantic v2)
    - Zero imports from `production/agent/tools.py` (no circular deps)
  - **Depends on**: None
  - **Test needed**: No (Pydantic self-validates; exercised in T006/T008/T012/T014/T021)

- [ ] T002 [P] Create `production/agent/prompts.py` — `build_system_prompt(channel, customer_name) -> str` (plan T-002)
  - **File**: `production/agent/prompts.py` (REPLACE stub)
  - **Acceptance**:
    - `build_system_prompt(channel: str, customer_name: str) -> str` callable
    - `datetime.now(ZoneInfo("Asia/Karachi"))` inside function body — NOT at module import time
    - Output contains PKT datetime in format `"Weekday, Month DD, YYYY at HH:MM AM/PM PKT"`
    - Output contains NexaFlow context: company name, "B2B SaaS workflow automation", plan tiers (Starter free / Growth $49/mo / Enterprise $199/mo), support hours (AI 24/7 / Human Mon–Fri 9am–6pm PKT)
    - Channel-specific tone block selected by `channel`:
      - `email` → complete paragraphs; body ≤ 2000 chars; no greeting/sign-off in body
      - `whatsapp` → ≤ 3 sentences; body ≤ 250 chars preferred; plain text; no greeting
      - `web_form` → structured next steps; body ≤ 4500 chars; no greeting
      - unknown channel → default professional block
    - All 7 ALWAYS rules verbatim from spec §Guardrails embedded
    - All 8 NEVER rules verbatim from spec §Guardrails embedded
    - `customer_name` present in output (ALWAYS-5: first-name rule)
  - **Depends on**: None
  - **Test needed**: No (exercised in T016/T025 agent run)

- [ ] T003 [P] Create `production/agent/formatters.py` — `FormattedResponse` + 3 channel formatters (plan T-003)
  - **File**: `production/agent/formatters.py` (REPLACE stub)
  - **Acceptance**:
    - `@dataclass FormattedResponse(formatted_text: str, channel: str, formatting_notes: list[str])`
    - `format_email_response(text: str, customer_name: str) -> FormattedResponse`:
      - Prepends `"Dear [FirstName],"` — no duplicate if already present
      - Appends NexaFlow signature block — no duplicate if already present
      - Word count ≤ 500; truncation → `formatting_notes` records `"truncated_to_500_words"`
      - Notes record `"added_greeting"` and `"added_signature"` when applied
    - `format_whatsapp_response(text: str, customer_name: str) -> FormattedResponse`:
      - Prepends `"Hi [FirstName]! 👋"`
      - Strips markdown headers (`#`, `##`) and list markers (`- `, `* `)
      - Truncates at last complete sentence before 1600 chars; notes record `"truncated_at_1600_chars"`
    - `format_web_form_response(text: str, customer_name: str) -> FormattedResponse`:
      - Prepends `"Hi [FirstName],"`
      - Allows light markdown (bold `**`, short bullet lists)
      - Truncates at 1000 chars / 300 words (whichever first); notes record transformation
    - All three: `customer_name.split()[0]` for first-name extraction
    - No import of `Channel` enum from `src/agent/models.py`
    - Port `_split_sentences()` helper from `src/agent/channel_formatter.py` unchanged
  - **Depends on**: None
  - **Test needed**: No (exercised via T012 send_response tests)

**Checkpoint**: T001 + T002 + T003 complete — `tools.py` and `customer_success_agent.py` can now be implemented.

---

## Phase 3: User Story 1 — New Customer Submits a Support Ticket (Priority: P1) 🎯 MVP

**Goal**: Full ticket lifecycle — create ticket → search KB → channel-appropriate response → resolve.
Agent definition, Runner wrapper, and RunResult parser live in this phase.

**Independent Test**: `pytest production/tests/test_agent_tools.py -k "search_kb or create_ticket or customer_history or send_response or resolve_ticket"` — all pass without `DATABASE_URL` or `OPENAI_API_KEY`.

### Test Scaffold (write first)

- [ ] T004 [US1] Create `production/tests/test_agent_tools.py` — scaffold: imports, fixtures, asyncio config (plan T-006 scaffold)
  - **File**: `production/tests/test_agent_tools.py` (NEW)
  - **Acceptance**:
    - File exists; `pytest production/tests/test_agent_tools.py` runs 0 tests, 0 errors
    - `asyncio_mode = "auto"` configured (conftest or pytest.ini)
    - `@pytest.fixture mock_pool` — `MagicMock` with `AsyncMock` for pool operations (no live DB)
    - `@pytest.fixture mock_openai_client` — patches `production.agent.tools._get_openai_client` return value
    - Does not break existing 101 tests
  - **Depends on**: None
  - **Test needed**: Yes — `pytest production/tests/test_agent_tools.py` returns exit 0

### Tools — search, create, history, send, resolve

- [ ] T005 ⚠️ HIGH RISK [US1] Create `production/agent/tools.py` with OpenAI client factory + `search_knowledge_base` (plan T-004a)
  - **File**: `production/agent/tools.py` (REPLACE stub)
  - **Acceptance**:
    - Module-level `_openai_client: AsyncOpenAI | None = None`
    - `def _get_openai_client() -> AsyncOpenAI` — initialises from `os.environ["OPENAI_API_KEY"]` on first call (lazy singleton)
    - `from production.database.queries import get_db_pool` and `from production.database import queries` present
    - `@function_tool async def search_knowledge_base(params: SearchKBInput) -> str`
      - `client = _get_openai_client()`
      - `resp = await client.embeddings.create(model="text-embedding-3-small", input=params.query)`
      - `embedding = resp.data[0].embedding`
      - `pool = await get_db_pool()`
      - `results = await queries.search_knowledge_base(pool, embedding, params.limit)`
      - Returns `json.dumps({"results": [...], "count": len(results)})`
      - Empty → `{"results": [], "count": 0}` (not error)
      - Exception → `{"error": str(e), "tool": "search_knowledge_base"}` (no naked raise; logs to stderr)
  - **Depends on**: T001 (SearchKBInput), Phase 4A `queries.search_knowledge_base`
  - **Test needed**: Yes → T006

- [ ] T006 [US1] Write unit tests for `search_knowledge_base` in `production/tests/test_agent_tools.py` (plan T-006a)
  - **File**: `production/tests/test_agent_tools.py` (MODIFY)
  - **Acceptance**:
    - `test_search_knowledge_base_happy_path`: mock embeddings + mock pool returns 2 results → JSON `count == 2`
    - `test_search_knowledge_base_empty_results`: mock pool returns `[]` → `{"results": [], "count": 0}`
    - `test_search_knowledge_base_db_error`: mock pool raises `asyncpg.PostgresError` → `{"error": "...", "tool": "search_knowledge_base"}`
    - All 3 pass; `pytest production/tests/` total ≥ 104 tests; existing 101 unbroken
  - **Depends on**: T004 (scaffold), T005 (implementation)
  - **Test needed**: Yes — `pytest production/tests/test_agent_tools.py::test_search_knowledge_base*`

- [ ] T007 ⚠️ HIGH RISK [US1] Add `create_ticket` tool to `production/agent/tools.py` (plan T-004b)
  - **File**: `production/agent/tools.py` (MODIFY — append function)
  - **Acceptance**:
    - `@function_tool async def create_ticket(params: CreateTicketInput) -> str`
    - `pool = await get_db_pool()`
    - Calls `await queries.create_ticket(pool, params.conversation_id, params.customer_id, params.channel, params.subject, params.category)`
    - Returns `json.dumps({"ticket_id": ..., "customer_id": ..., "conversation_id": ..., "channel": ..., "status": "open", "created_at": str(row["created_at"])})`
    - DB error → `{"error": str(e), "tool": "create_ticket"}` (no naked raise)
  - **Depends on**: T001 (CreateTicketInput), T005 (module exists)
  - **Test needed**: Yes → T008

- [ ] T008 [US1] Write unit tests for `create_ticket` in `production/tests/test_agent_tools.py` (plan T-006b)
  - **File**: `production/tests/test_agent_tools.py` (MODIFY)
  - **Acceptance**:
    - `test_create_ticket_happy_path`: mock pool → JSON has `ticket_id` (non-null string)
    - `test_create_ticket_invalid_channel_pydantic`: `CreateTicketInput(channel="fax", ...)` — tool still accepts (channel validated by DB, not schema); OR pydantic rejects if constrained (check contracts — channel is plain str, no constraint in schema so tool should accept)
    - `test_create_ticket_db_error`: mock pool raises `asyncpg.UniqueViolationError` → `{"error": "...", "tool": "create_ticket"}`
    - All 3 pass; no existing tests broken
  - **Depends on**: T004, T007
  - **Test needed**: Yes

- [ ] T009 ⚠️ HIGH RISK [US1] Add `get_customer_history` tool to `production/agent/tools.py` (plan T-004c)
  - **File**: `production/agent/tools.py` (MODIFY — append function)
  - **Acceptance**:
    - `@function_tool async def get_customer_history(customer_id: Annotated[str, Field(description="Customer UUID")], limit: int = 20) -> str`
    - `pool = await get_db_pool()`
    - Calls `await queries.get_customer_history(pool, customer_id, limit)`
    - Returns `json.dumps({"conversations": [...], "count": len(conversations)})`
    - Empty → `{"conversations": [], "count": 0}` (not error)
    - Exception → `{"error": str(e), "tool": "get_customer_history"}` (no naked raise)
  - **Depends on**: T005 (module exists), Phase 4A `queries.get_customer_history`
  - **Test needed**: Yes → T010

- [ ] T010 [US1] Write unit tests for `get_customer_history` in `production/tests/test_agent_tools.py` (plan T-006c)
  - **File**: `production/tests/test_agent_tools.py` (MODIFY)
  - **Acceptance**:
    - `test_get_customer_history_happy_path`: mock pool returns 2 conversations → JSON `count == 2`
    - `test_get_customer_history_empty`: mock returns `[]` → `{"conversations": [], "count": 0}`
    - `test_get_customer_history_db_error`: mock raises → `{"error": "...", "tool": "get_customer_history"}`
    - All 3 pass; no existing tests broken
  - **Depends on**: T004, T009
  - **Test needed**: Yes

- [ ] T011 ⚠️ HIGH RISK [US1] Add `send_response` tool to `production/agent/tools.py` (plan T-004e)
  - **File**: `production/agent/tools.py` (MODIFY — append function)
  - **Acceptance**:
    - `@function_tool async def send_response(params: SendResponseInput) -> str`
    - Imports and calls correct formatter: `format_email_response` / `format_whatsapp_response` / `format_web_form_response` based on `params.channel`
    - Stub delivery: `print(f"[STUB] {params.channel}: {formatted.formatted_text[:80]}...")` to console
    - Returns `json.dumps({"delivery_status": "stub_delivered", "ticket_id": params.ticket_id, "channel": params.channel, "message_length": len(formatted.formatted_text), "timestamp": datetime.utcnow().isoformat() + "Z"})`
    - Channel limits enforced (formatter truncates; no rejection)
    - Exception → `{"error": str(e), "tool": "send_response"}` (no naked raise)
  - **Depends on**: T001 (SendResponseInput), T003 (formatters), T005 (module)
  - **Test needed**: Yes → T012

- [ ] T012 [US1] Write unit tests for `send_response` in `production/tests/test_agent_tools.py` (plan T-006e)
  - **File**: `production/tests/test_agent_tools.py` (MODIFY)
  - **Acceptance**:
    - `test_send_response_email_truncation`: 600-word input → `message_length` ≤ (500-word character equivalent); `delivery_status == "stub_delivered"`
    - `test_send_response_whatsapp_stub`: valid whatsapp message ≤ 1600 chars → `delivery_status == "stub_delivered"`, `channel == "whatsapp"`
    - `test_send_response_missing_message_raises`: `SendResponseInput(message="")` raises `pydantic.ValidationError`
    - All 3 pass; no existing tests broken
  - **Depends on**: T004, T011
  - **Test needed**: Yes

- [ ] T013 ⚠️ HIGH RISK [US1] Add `resolve_ticket` tool to `production/agent/tools.py` (plan T-004g)
  - **File**: `production/agent/tools.py` (MODIFY — append function)
  - **Acceptance**:
    - `@function_tool async def resolve_ticket(params: ResolveTicketInput) -> str`
    - `pool = await get_db_pool()`
    - Calls `await queries.update_ticket_status(pool, params.ticket_id, status="resolved", reason=params.resolution_summary)`
    - Returns `json.dumps({"ticket_id": ..., "status": "resolved", "resolution_summary": ..., "resolved_at": ...})`
    - Idempotent: already-RESOLVED → returns existing record, no error
    - ESCALATED ticket → `{"error": "cannot resolve escalated ticket", "tool": "resolve_ticket"}`
    - Exception → `{"error": str(e), "tool": "resolve_ticket"}` (no naked raise)
  - **Depends on**: T001 (ResolveTicketInput), T005 (module), Phase 4A `queries.update_ticket_status`
  - **Test needed**: Yes → T014

- [ ] T014 [US1] Write unit tests for `resolve_ticket` in `production/tests/test_agent_tools.py` (plan T-006g)
  - **File**: `production/tests/test_agent_tools.py` (MODIFY)
  - **Acceptance**:
    - `test_resolve_ticket_happy_path`: mock pool returns resolved row → `status == "resolved"`
    - `test_resolve_ticket_idempotent`: mock returns already-resolved row → no error in JSON
    - `test_resolve_ticket_escalated_blocked`: mock raises or returns escalated state → `{"error": "cannot resolve escalated ticket", "tool": "resolve_ticket"}`
    - All 3 pass; no existing tests broken
  - **Depends on**: T004, T013
  - **Test needed**: Yes

### Agent Core (definition → runner → parser)

- [ ] T015 ⚠️ HIGH RISK [US1] Define `AgentResponse` + `CustomerContext` dataclasses in `production/agent/customer_success_agent.py` (plan T-005 prep)
  - **File**: `production/agent/customer_success_agent.py` (REPLACE stub)
  - **Acceptance**:
    - `@dataclass AgentResponse`: `ticket_id: str | None`, `response_text: str`, `channel: str`, `escalated: bool = False`, `escalation_id: str | None = None`, `resolution_status: str = "pending"`, `error: str | None = None`
    - `@dataclass CustomerContext`: `customer_id: str`, `customer_name: str`, `customer_email: str`, `channel: str`, `message: str`, `conversation_id: str | None = None`
    - Both importable from `production.agent.customer_success_agent`
    - No circular imports (no import of `tools.py` at module level yet)
  - **Depends on**: None (pure dataclasses)
  - **Test needed**: No

- [ ] T016 ⚠️ HIGH RISK [US1] Implement `Agent` definition inside `process_ticket()` in `production/agent/customer_success_agent.py` (plan T-005a)
  - **File**: `production/agent/customer_success_agent.py` (MODIFY)
  - **Acceptance**:
    - `async def process_ticket(ctx: CustomerContext) -> AgentResponse` defined
    - `queries.get_or_create_customer(pool, ctx.customer_email, ctx.customer_name)` called before prompt build
    - `queries.create_conversation(pool, customer_id, ctx.channel)` called if `ctx.conversation_id is None`
    - `Agent(name="NexaFlow Customer Success", instructions=build_system_prompt(ctx.channel, ctx.customer_name), model="gpt-4o-mini", tools=[search_knowledge_base, create_ticket, get_customer_history, escalate_to_human, send_response, get_sentiment_trend, resolve_ticket])` constructed INSIDE `process_ticket` (not module-level)
    - Agent construction uses `build_system_prompt` from `production.agent.prompts`
    - All 7 tools from `production.agent.tools` imported and passed as list
  - **Depends on**: T002 (prompts), T005–T013 (all tools), T015 (dataclasses)
  - **Test needed**: No (exercised in T017 runner step)

- [ ] T017 ⚠️ HIGH RISK [US1] Add `Runner.run()` call + retry logic to `process_ticket()` in `production/agent/customer_success_agent.py` (plan T-005b)
  - **File**: `production/agent/customer_success_agent.py` (MODIFY)
  - **Acceptance**:
    - `result = await Runner.run(agent, ctx.message)` called
    - First `openai.APIError` caught → retry once: `result = await Runner.run(agent, ctx.message)`
    - Second `openai.APIError` → best-effort `escalate_to_human` call → returns `AgentResponse(escalated=True, error=str(e), response_text="", channel=ctx.channel)`
    - `openai.AuthenticationError` and `openai.PermissionDeniedError` NOT caught — bubble to caller
    - No other `Exception` types silently swallowed (only `APIError` is retried)
  - **Depends on**: T016 (Agent definition)
  - **Test needed**: No (tested via T027 integration)

- [ ] T018 ⚠️ HIGH RISK [US1] Add `RunResult` → `AgentResponse` parser to `process_ticket()` in `production/agent/customer_success_agent.py` (plan T-005c)
  - **File**: `production/agent/customer_success_agent.py` (MODIFY)
  - **Acceptance**:
    - `AgentResponse.response_text = result.final_output` (str)
    - `ticket_id` extracted: scan `result` tool call outputs for `create_ticket` result; parse `ticket_id` from JSON
    - `escalated` set `True` if any tool call in result is `escalate_to_human`
    - `escalation_id` populated from `escalate_to_human` result JSON if present
    - `resolution_status` set to `"resolved"` if `resolve_ticket` call is present in result; else `"pending"`
    - Returns complete `AgentResponse` with all fields populated from result
  - **Depends on**: T017 (Runner call)
  - **Test needed**: No (tested via T025 integration)

**Checkpoint**: US1 complete — `process_ticket()` handles new customer end-to-end. Run `pytest production/tests/test_agent_tools.py` — all 21+ unit tests pass.

---

## Phase 4: User Story 2 — Returning Customer Acknowledged Across Channels (Priority: P2)

**Goal**: Channel-aware tone injection in system prompt; cross-channel history acknowledgment enforced via ALWAYS-3 rule.

**Independent Test**: Call `build_system_prompt(channel="whatsapp", customer_name="Alice")` — WhatsApp tone block present. `build_system_prompt("email", "Bob")` — email block. `build_system_prompt("sms", "Carol")` — default block. No code changes needed to test this — T002 prompts.py already covers it.

- [ ] T019 ⚠️ HIGH RISK [US2] Wire channel-aware instruction into `process_ticket()` in `production/agent/customer_success_agent.py` (plan T-005d)
  - **File**: `production/agent/customer_success_agent.py` (MODIFY)
  - **Acceptance**:
    - `ctx.channel` passed correctly to `build_system_prompt(ctx.channel, ctx.customer_name)` — confirmed in T016; this task verifies and documents, adds assertion/log
    - `build_system_prompt` called with `channel="email"` → system prompt contains email tone block
    - `build_system_prompt` called with `channel="whatsapp"` → system prompt contains WhatsApp tone block
    - `build_system_prompt` called with `channel="web_form"` → system prompt contains web_form tone block
    - Unknown channel → default tone block (ALWAYS rule: never error on unknown channel)
    - ALWAYS-3 rule (`get_customer_history` on every interaction) explicitly stated in system prompt
    - Cross-channel history acknowledgment instruction present for all channel values
  - **Depends on**: T018 (full process_ticket), T002 (prompts.py)
  - **Test needed**: No (prompts.py self-documents; validated in T028 channel format integration test)

**Checkpoint**: US2 complete — returning customers across all 3 channels receive correct tone; prior history is referenced.

---

## Phase 5: User Story 3 — Sentiment-Triggered Escalation (Priority: P3)

**Goal**: `escalate_to_human` tool with idempotency guard + `get_sentiment_trend` with trend computation and recommend_escalation logic.

**Independent Test**: `pytest production/tests/test_agent_tools.py -k "escalate or sentiment"` — all 6 tests pass without live DB.

- [ ] T020 ⚠️ HIGH RISK [US3] Add `escalate_to_human` tool to `production/agent/tools.py` (plan T-004d)
  - **File**: `production/agent/tools.py` (MODIFY — append function)
  - **Acceptance**:
    - `@function_tool async def escalate_to_human(params: EscalateInput) -> str`
    - `escalation_id = str(uuid.uuid4())` generated inside tool (queries.update_ticket_status does not return one)
    - `pool = await get_db_pool()`
    - Calls `await queries.update_ticket_status(pool, params.ticket_id, status="escalated", reason=params.reason)`
    - Returns `json.dumps({"escalation_id": escalation_id, "ticket_id": params.ticket_id, "status": "escalated", "reason": params.reason, "urgency": params.urgency, "escalated_at": datetime.utcnow().isoformat() + "Z"})`
    - Idempotent: re-escalating an already-ESCALATED ticket returns existing record format without error
    - Exception → `{"error": str(e), "tool": "escalate_to_human"}` (no naked raise)
  - **Depends on**: T001 (EscalateInput), T005 (module), Phase 4A `queries.update_ticket_status`
  - **Test needed**: Yes → T021

- [ ] T021 [US3] Write unit tests for `escalate_to_human` in `production/tests/test_agent_tools.py` (plan T-006d)
  - **File**: `production/tests/test_agent_tools.py` (MODIFY)
  - **Acceptance**:
    - `test_escalate_to_human_happy_path`: mock pool → JSON has `escalation_id` (valid UUID), `status == "escalated"`
    - `test_escalate_to_human_empty_reason_raises`: `EscalateInput(ticket_id="x", reason="")` raises `pydantic.ValidationError` (min_length=1)
    - `test_escalate_to_human_idempotent`: mock returns already-escalated record → no error; `escalation_id` present in response
    - All 3 pass; no existing tests broken
  - **Depends on**: T004, T020
  - **Test needed**: Yes

- [ ] T022 ⚠️ HIGH RISK [US3] Add `get_sentiment_trend` tool to `production/agent/tools.py` (plan T-004f)
  - **File**: `production/agent/tools.py` (MODIFY — append function)
  - **Acceptance**:
    - `@function_tool async def get_sentiment_trend(customer_id: Annotated[str, Field(description="Customer UUID")], last_n: int = 5) -> str`
    - `pool = await get_db_pool()`
    - Calls `await queries.get_sentiment_trend(pool, customer_id, last_n)` → returns `list[float]`
    - Trend logic computed in tool (not DB):
      - `improving`: `scores[-1] > scores[0] + 0.2`
      - `deteriorating`: `scores[-1] < scores[0] - 0.2`
      - `stable`: otherwise (including len < 2)
    - `recommend_escalation = statistics.mean(scores) < 0.3` (True if avg < 0.3)
    - Returns `json.dumps({"scores": scores, "count": len(scores), "trend": trend, "recommend_escalation": recommend_escalation})`
    - Empty → `{"scores": [], "count": 0, "trend": "insufficient_data", "recommend_escalation": false}`
    - Exception → `{"error": str(e), "tool": "get_sentiment_trend"}` (no naked raise)
  - **Depends on**: T005 (module), Phase 4A `queries.get_sentiment_trend`
  - **Test needed**: Yes → T023

- [ ] T023 [US3] Write unit tests for `get_sentiment_trend` in `production/tests/test_agent_tools.py` (plan T-006f)
  - **File**: `production/tests/test_agent_tools.py` (MODIFY)
  - **Acceptance**:
    - `test_sentiment_trend_improving`: scores `[0.2, 0.4, 0.6]` → `trend == "improving"`, `recommend_escalation == False` (avg 0.4)
    - `test_sentiment_trend_deteriorating_escalation`: scores `[0.5, 0.2, 0.1]` → `trend == "deteriorating"` (0.1 < 0.5−0.2=0.3), `recommend_escalation == True` (avg 0.267 < 0.3)
    - `test_sentiment_trend_empty`: mock returns `[]` → `{"scores": [], "count": 0, "trend": "insufficient_data", "recommend_escalation": false}`
    - All 3 pass; `pytest production/tests/test_agent_tools.py` total ≥ 27 tests; existing 101 unbroken
  - **Depends on**: T004, T022
  - **Test needed**: Yes

**Checkpoint**: US3 complete — all 7 tools implemented and unit-tested. Run full suite: `pytest production/tests/` — all tests pass.

---

## Phase 6: Polish & Cross-Cutting Concerns — Integration Tests

**Purpose**: End-to-end validation of the full agent pipeline. All 5 integration scenarios from plan T-007.

- [ ] T024 Create `production/tests/test_agent_integration.py` — scaffold + skip guard (plan T-007 scaffold)
  - **File**: `production/tests/test_agent_integration.py` (NEW)
  - **Acceptance**:
    - `pytestmark = pytest.mark.skipif(not os.environ.get("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL not set")` at module level
    - File imports `process_ticket`, `CustomerContext`, `AgentResponse`
    - `pytest production/tests/test_agent_integration.py` skips gracefully without `TEST_DATABASE_URL` — no errors
    - Does not break existing 101 tests
  - **Depends on**: T015–T018 (full process_ticket)
  - **Test needed**: Yes — `pytest production/tests/test_agent_integration.py` returns exit 0 (skipped)

- [ ] T025 [P] Write `TestNewCustomerFlow` in `production/tests/test_agent_integration.py` (plan T-007 — full run)
  - **File**: `production/tests/test_agent_integration.py` (MODIFY)
  - **Acceptance**:
    - `test_new_customer_full_run`: mocked DB pool (no real Neon); mock `Runner.run` returning a `RunResult` with `create_ticket` + `send_response` tool calls and `final_output`
    - `AgentResponse.ticket_id` is non-null
    - `AgentResponse.resolution_status` in `{"pending", "resolved"}`
    - `AgentResponse.error` is None
    - Test passes without `OPENAI_API_KEY` (Runner.run is mocked)
  - **Depends on**: T024 (scaffold)
  - **Test needed**: Yes

- [ ] T026 [P] Write `TestToolCallOrdering` in `production/tests/test_agent_integration.py` (plan T-007 — ordering)
  - **File**: `production/tests/test_agent_integration.py` (MODIFY)
  - **Acceptance**:
    - `test_create_ticket_before_send_response`: mock RunResult trace contains `create_ticket` call before any `send_response` call
    - Parse `RunResult` tool call list (or mock constructed call order) to verify ordering
    - Test fails if `send_response` appears before `create_ticket` in tool call trace
  - **Depends on**: T024
  - **Test needed**: Yes

- [ ] T027 [P] Write `TestAPIErrorRetry` in `production/tests/test_agent_integration.py` (plan T-007 — retry)
  - **File**: `production/tests/test_agent_integration.py` (MODIFY)
  - **Acceptance**:
    - `test_api_error_retry_escalates`: mock `Runner.run` to raise `openai.APIError` on both calls (first attempt + retry)
    - `AgentResponse.escalated == True`
    - `AgentResponse.error` is non-null string
    - No unhandled exception propagates (return, not raise)
    - Test passes without real OpenAI connection
  - **Depends on**: T024
  - **Test needed**: Yes

- [ ] T028 [P] Write `TestChannelFormatting` in `production/tests/test_agent_integration.py` (plan T-007 — channel)
  - **File**: `production/tests/test_agent_integration.py` (MODIFY)
  - **Acceptance**:
    - `test_email_response_within_limit`: mock RunResult with email channel → verify `response_text` fits within 500-word limit
    - `test_whatsapp_response_within_limit`: whatsapp channel → `len(response_text)` ≤ 1600 chars
    - `test_web_form_response_within_limit`: web_form channel → `len(response_text)` ≤ 1000 chars
    - All 3 pass with mocked Runner (no real OpenAI)
  - **Depends on**: T024
  - **Test needed**: Yes

- [ ] T029 [P] Write `TestEscalationPath` in `production/tests/test_agent_integration.py` (plan T-007 — escalation)
  - **File**: `production/tests/test_agent_integration.py` (MODIFY)
  - **Acceptance**:
    - `test_sentiment_escalation`: mock `Runner.run` returns RunResult with `get_sentiment_trend` output `[0.2, 0.1, 0.25]` and `escalate_to_human` tool call → `AgentResponse.escalated == True`
    - `test_explicit_human_request_escalation`: message contains "talk to a manager" → mock confirms `escalate_to_human` in tool calls → `AgentResponse.escalated == True`
    - Both pass with mocked Runner + mocked DB pool
  - **Depends on**: T024
  - **Test needed**: Yes

---

## Dependencies & Execution Order

### Phase Dependencies

- **Foundational (Phase 2)**: No deps — start immediately. T002 and T003 are parallel to T001.
- **Phase 3 (US1)**: Depends on Phase 2 complete (T001 for schemas, T002 for prompts, T003 for formatters)
  - T004 (scaffold) can start as soon as Phase 2 begins
  - T005 depends on T001
  - T007/T009/T011/T013 each depend on T005 (module exists)
  - T006/T008/T010/T012/T014 each depend on their tool + T004 scaffold
  - T015 has no deps; T016 needs T002+T005–T013; T017 needs T016; T018 needs T017
- **Phase 4 (US2)**: Depends on T018 (full process_ticket) + T002 (prompts)
- **Phase 5 (US3)**: Depends on T005 (module) + T001 (schemas)
- **Phase 6 (Integration)**: Depends on T015–T018 (full agent); T025–T029 are parallel after T024 scaffold

### User Story Dependencies

| Story | Can start after | Deps on other stories |
|-------|----------------|----------------------|
| US1 (P1) | Phase 2 complete | None |
| US2 (P2) | T018 (process_ticket complete) | Shares prompts.py with US1 |
| US3 (P3) | T001 + T005 module exists | None (tools are independent) |

### Within Each Phase

- Tool tasks (T005, T007, T009, T011, T013, T020, T022): each adds one function to tools.py — strictly sequential
- Unit tests (T006, T008, T010, T012, T014, T021, T023): each immediately follows its tool task
- Integration tests (T025–T029): parallel after scaffold T024

### Parallel Opportunities

```bash
# Phase 2 — all three in parallel
T001 schemas.py  |  T002 prompts.py  |  T003 formatters.py

# Phase 3 — test scaffold is independent
T004 (scaffold)  — can start immediately alongside Phase 2

# Phase 5 — US3 tools are parallel to US2 (T019)
T020 escalate_to_human  |  T022 get_sentiment_trend  (after T005 exists)

# Phase 6 — integration tests run in parallel
T025 full run  |  T026 ordering  |  T027 retry  |  T028 channel  |  T029 escalation
```

---

## Parallel Examples

```bash
# Start of project — all parallel
Task T001: Create production/agent/schemas.py
Task T002: Create production/agent/prompts.py
Task T003: Create production/agent/formatters.py
Task T004: Create production/tests/test_agent_tools.py scaffold

# Phase 5 — parallel after T005 module exists
Task T020: Add escalate_to_human to tools.py
Task T022: Add get_sentiment_trend to tools.py  # after T020 adds function

# Phase 6 — all integration tests parallel after T024 scaffold
Task T025 T026 T027 T028 T029 (all in test_agent_integration.py, different test classes)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 2: T001, T002, T003
2. Complete Phase 3: T004–T018
3. **STOP and VALIDATE**: `pytest production/tests/` — all pass
4. Demo: `process_ticket()` with web_form channel, new customer

### Incremental Delivery

1. Phase 2 (Foundational) → run `python -c "from production.agent.schemas import SearchKBInput"`
2. Phase 3 (US1) → `pytest production/tests/test_agent_tools.py` — 21+ tests pass
3. Phase 4 (US2) → verify channel tone blocks via `build_system_prompt()`
4. Phase 5 (US3) → `pytest production/tests/test_agent_tools.py -k "escalate or sentiment"` — 6 tests pass
5. Phase 6 (Integration) → `pytest production/tests/test_agent_integration.py` (skip if no `TEST_DATABASE_URL`)

---

## Task Summary

| Phase | Tasks | Plan Tasks Covered | HIGH RISK count |
|-------|-------|-------------------|-----------------|
| 2 (Foundational) | T001–T003 | T-001, T-002, T-003 | 0 |
| 3 (US1 core) | T004–T018 | T-004a/b/c/e/g, T-005a/b/c, T-006 (partial) | 9 |
| 4 (US2 channel) | T019 | T-005d | 1 |
| 5 (US3 escalation) | T020–T023 | T-004d/f, T-006 (partial) | 2 |
| 6 (Integration) | T024–T029 | T-007 | 0 |
| **Total** | **29** | **T-001 through T-007 (all)** | **12** |

**Total tasks**: 29
**HIGH RISK subtasks**: T005, T007, T009, T011, T013, T015, T016, T017, T018, T019, T020, T022 (12 total)

### Plan sub-task → Task ID mapping

| Plan sub-task | Task ID | Description |
|--------------|---------|-------------|
| T-001 | T001 | schemas.py — 5 Pydantic models |
| T-002 | T002 | prompts.py — build_system_prompt |
| T-003 | T003 | formatters.py — 3 formatters |
| T-004a | T005 | search_knowledge_base |
| T-004b | T007 | create_ticket |
| T-004c | T009 | get_customer_history |
| T-004d | T020 | escalate_to_human |
| T-004e | T011 | send_response |
| T-004f | T022 | get_sentiment_trend |
| T-004g | T013 | resolve_ticket |
| T-005a | T015 + T016 | dataclasses + Agent definition |
| T-005b | T017 | Runner wrapper + retry |
| T-005c | T018 | RunResult parser |
| T-005d | T019 | channel-aware instructions |
| T-006 | T004 + T006 + T008 + T010 + T012 + T014 + T021 + T023 | unit test scaffold + per-tool tests |
| T-007 | T024 + T025 + T026 + T027 + T028 + T029 | integration tests (5 scenarios) |
