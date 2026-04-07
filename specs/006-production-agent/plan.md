# Implementation Plan: Production Agent — Phase 4B

**Branch**: `006-production-agent` | **Date**: 2026-04-04
**Spec**: `specs/006-production-agent/spec.md`
**Research**: `specs/006-production-agent/research.md`
**Data Model**: `specs/006-production-agent/data-model.md`
**Contracts**: `specs/006-production-agent/contracts/tools.md`

---

## Summary

Implement the production OpenAI Agents SDK agent for NexaFlow Customer Success.
Phase 4B delivers 6 files: `tools.py` (7 @function_tool functions backed by asyncpg queries),
`prompts.py` (PKT-datetime-injected system prompt), `formatters.py` (3 channel formatters),
`customer_success_agent.py` (Agent definition + `process_ticket()` with error handling), and
2 test files. All files replace stubs in `production/agent/` that read
`# Phase 4X will implement this`. The DB layer (Phase 4A) is complete; the channel dispatch
layer (Phase 4C) is NOT yet implemented — `send_response` stubs delivery in this phase.

---

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: `openai-agents` (OpenAI Agents SDK), `asyncpg` (Neon PostgreSQL),
`pydantic>=2.0`, `openai>=1.0` (for embeddings), `python-dotenv`
**Storage**: Neon PostgreSQL 16 + pgvector (via `production/database/queries.py` — Phase 4A complete)
**Testing**: `pytest`, `pytest-asyncio`, `pytest-mock` (unit); live DB optional for integration
**Target Platform**: Linux server (WSL2 dev, Oracle Cloud VM prod), Python 3.12
**Project Type**: Single Python package under `production/`
**Performance Goals**: P95 tool call latency < 3s (all tools); end-to-end < 2 min
**Constraints**: gpt-4o-mini model only; `send_response` stubs delivery (Phase 4C wires real dispatch); no new DB schema changes
**Scale/Scope**: ~800 tickets/week; 7 tools; 3 channels

---

## Constitution Check

*GATE: Must pass before implementation begins.*

| Gate | Rule | Status | Notes |
|------|------|--------|-------|
| Datetime injection | ALWAYS-1: inject PKT datetime on every invocation | ✅ PASS | `build_system_prompt()` calls `datetime.now(ZoneInfo("Asia/Karachi"))` on every call |
| Tool call ordering | ALWAYS-2: `create_ticket` before `send_response` | ✅ PASS | Structural: `send_response` requires `ticket_id` (only available after `create_ticket`) |
| Cross-channel history | ALWAYS-3: `get_customer_history` on every interaction | ✅ PASS | System prompt ALWAYS rule embedded |
| Sentiment before close | ALWAYS-4: sentiment score before ticket close | ✅ PASS | System prompt ALWAYS rule embedded; `get_sentiment_trend` available |
| Channel limits | NEVER-6: email ≤500w, WhatsApp ≤1600c, web_form ≤1000c | ✅ PASS | Enforced in `send_response` tool + formatters |
| No competitor names | NEVER-1 | ✅ PASS | Embedded in system prompt |
| No date guessing | NEVER-4 | ✅ PASS | PKT datetime injected; NEVER rule in prompt |
| Technology lock | Constitution §VI: OpenAI Agents SDK (`agents` package) | ✅ PASS | Using `agents.Agent`, `agents.Runner`, `@function_tool` |
| Pydantic v2 | Constitution §VI: FastAPI uses Pydantic v2 | ✅ PASS | All tool input models use Pydantic v2 `BaseModel` |
| Secrets policy | Never hardcode API keys | ✅ PASS | All credentials via `os.environ` |

**No violations. No complexity tracking required.**

---

## Project Structure

### Documentation (this feature)

```text
specs/006-production-agent/
├── plan.md              ← this file
├── spec.md              ← authoritative requirements (14/14 checklist)
├── research.md          ← Phase 0 output (5 unknowns resolved)
├── data-model.md        ← Phase 1 output (entities + Pydantic models)
├── quickstart.md        ← Phase 1 output (how to run)
├── contracts/
│   └── tools.md         ← Phase 1 output (7 tool I/O contracts)
├── checklists/
│   └── requirements.md  ← spec quality checklist (all passed)
└── tasks.md             ← Phase 2 output (/sp.tasks — NOT yet created)
```

### Source Code

```text
production/
├── agent/
│   ├── __init__.py              (exists — no changes)
│   ├── schemas.py               ← T-001 NEW: 5 Pydantic input models
│   ├── prompts.py               ← T-002 REPLACE stub: build_system_prompt()
│   ├── formatters.py            ← T-003 REPLACE stub: 3 formatters + FormattedResponse
│   ├── tools.py                 ← T-004 REPLACE stub: 7 @function_tool functions [HIGH RISK]
│   └── customer_success_agent.py ← T-005 REPLACE stub: Agent + process_ticket() [HIGH RISK]
├── database/
│   └── queries.py               (Phase 4A — complete, no changes)
└── tests/
    ├── test_database.py         (Phase 4A — complete, no changes)
    ├── test_agent_tools.py      ← T-006 NEW: unit tests (mocked)
    └── test_agent_integration.py ← T-007 NEW: integration tests (live DB optional)
```

---

## Implementation Tasks

### T-001: production/agent/schemas.py — Pydantic Input Models

**Risk**: LOW
**Dependencies**: None
**Acceptance criteria**:
- [ ] `SearchKBInput(query: str, limit: int = 5)` — `query` max_length=500; `limit` ge=1, le=20
- [ ] `CreateTicketInput(customer_id, conversation_id, channel, subject=None, category=None)` — all fields with Field descriptions
- [ ] `EscalateInput(ticket_id, reason, urgency: str = "medium")` — `reason` min_length=1
- [ ] `SendResponseInput(ticket_id, message, channel)` — `message` min_length=1; `ticket_id` description: "UUID from create_ticket — call create_ticket first"
- [ ] `ResolveTicketInput(ticket_id, resolution_summary)` — `resolution_summary` min_length=1
- [ ] All models pass `model.model_json_schema()` without error (Pydantic v2 validation)
- [ ] No imports from `production/agent/tools.py` (zero circular dependency)

**Implementation notes**:
- Pure Pydantic v2 `BaseModel` classes; no logic, no DB calls
- All Field descriptions must be agent-readable (LLM sees these in JSON Schema)
- File exists standalone; imported by `tools.py`

---

### T-002: production/agent/prompts.py — System Prompt Builder

**Risk**: LOW
**Dependencies**: None (pure Python)
**Acceptance criteria**:
- [ ] `build_system_prompt(channel: str, customer_name: str) -> str` function exists and is callable
- [ ] PKT datetime is recomputed on every call: `datetime.now(ZoneInfo("Asia/Karachi"))` — NOT cached
- [ ] Output contains current date/time string matching format `"Weekday, Month DD, YYYY at HH:MM AM/PM PKT"`
- [ ] Output contains NexaFlow company context (name, plans, prices, support hours)
- [ ] Output contains channel-specific tone block for `email`, `whatsapp`, `web_form`; unrecognised channel falls back to default block
- [ ] Output contains all 7 ALWAYS rules verbatim from spec §Guardrails
- [ ] Output contains all 8 NEVER rules verbatim from spec §Guardrails
- [ ] Output contains `customer_name` (used by ALWAYS-5 first-name rule)
- [ ] `datetime.now()` is called inside the function body, not at module import time

**Implementation notes**:
- Port `src/agent/prompts.py::get_system_prompt()` — rename to `build_system_prompt()`
- Replace prototype's compact guidelines with full ALWAYS/NEVER rules from spec §8
- Expand channel instructions to match spec FR-033 (email ≤2000 chars body; WhatsApp ≤250 chars preferred; web_form ≤4500 chars)

---

### T-003: production/agent/formatters.py — Channel Formatters

**Risk**: LOW
**Dependencies**: None (pure Python)
**Acceptance criteria**:
- [ ] `FormattedResponse` dataclass with `formatted_text: str`, `channel: str`, `formatting_notes: list[str]`
- [ ] `format_email_response(text: str, customer_name: str) -> FormattedResponse`
  - Prepends `"Dear [FirstName],"` and appends NexaFlow signature
  - Does NOT duplicate greeting/signature if already present
  - `formatting_notes` records `"added_greeting"` and `"added_signature"` when applied
  - Word count enforced: ≤ 500 words; truncation recorded in notes
- [ ] `format_whatsapp_response(text: str, customer_name: str) -> FormattedResponse`
  - Prepends `"Hi [FirstName]! 👋"`
  - Strips markdown headers (`#`, `##`) and unordered lists (`-`, `*`) from body
  - Truncates at last complete sentence before 1600 chars; records in notes
  - `formatting_notes` records all transformations
- [ ] `format_web_form_response(text: str, customer_name: str) -> FormattedResponse`
  - Prepends `"Hi [FirstName],"`
  - Allows light markdown (bold, short bullet lists)
  - Truncates at 1000 chars / 300 words; records in notes
- [ ] All three functions use `customer_name.split()[0]` for first-name extraction

**Implementation notes**:
- Port `src/agent/channel_formatter.py` — limits updated to match spec (email 500 words, not 2500 chars)
- `Channel` enum from `src/agent/models.py` is NOT imported — use plain strings `"email"`, `"whatsapp"`, `"web_form"` to avoid cross-module dependency
- `_split_sentences()` helper is ported unchanged from prototype

---

### T-004: production/agent/tools.py — 7 @function_tool Functions ⚠️ HIGH RISK

**Risk**: HIGH
**Dependencies**: T-001 (schemas.py), `production/database/queries.py` (Phase 4A)
**Risk factors**:
- `asyncpg.Pool` must be awaited inside `@function_tool` async function (R-001)
- Embedding API call inside `search_knowledge_base` adds async dependency chain (R-002)
- All tools must return JSON strings (never raise) — requires broad exception handling
- `get_sentiment_trend` trend computation requires careful float comparison logic

**Acceptance criteria**:
- [ ] Module-level `_openai_client: AsyncOpenAI | None = None` with `_get_openai_client()` factory
- [ ] All 7 functions decorated with `@function_tool` and defined as `async def`
- [ ] `search_knowledge_base(params: SearchKBInput)` — embeds query, calls `queries.search_knowledge_base`, returns JSON
- [ ] `create_ticket(params: CreateTicketInput)` — calls `queries.create_ticket`, returns JSON with `ticket_id`
- [ ] `get_customer_history(customer_id: Annotated[str, ...], limit: int = 20)` — calls `queries.get_customer_history`, returns JSON
- [ ] `escalate_to_human(params: EscalateInput)` — calls `queries.update_ticket_status(status="escalated")`, returns JSON with `escalation_id` (generated UUID)
- [ ] `send_response(params: SendResponseInput)` — applies length enforcement (channel limits), logs stub, returns JSON
- [ ] `get_sentiment_trend(customer_id: Annotated[str, ...], last_n: int = 5)` — calls `queries.get_sentiment_trend`, computes trend label, recommends escalation if avg < 0.3
- [ ] `resolve_ticket(params: ResolveTicketInput)` — calls `queries.update_ticket_status(status="resolved")`, returns JSON; returns error JSON for ESCALATED tickets
- [ ] Every tool has a `try/except Exception` that logs to stderr and returns `{"error": str(e), "tool": "<name>"}` — no naked raises

**Implementation notes**:
- `escalate_to_human` generates its own `escalation_id` via `str(uuid.uuid4())` since `update_ticket_status` does not return one
- `send_response` calls the appropriate formatter (`format_email_response`, etc.) from `formatters.py` before stub delivery
- All tools import `from production.database.queries import get_db_pool` and `from production.database import queries`

---

### T-005: production/agent/customer_success_agent.py — Agent Definition + process_ticket() ⚠️ HIGH RISK

**Risk**: HIGH
**Dependencies**: T-001, T-002, T-003, T-004 (all agent files)
**Risk factors**:
- Tool call ordering enforced via system prompt + data dependency (ticket_id required in send_response) — LLM compliance is probabilistic
- OpenAI API retry logic must catch correct exception types (R-005)
- `process_ticket()` must extract `AgentResponse` from `RunResult.final_output` (str) — parsing required
- Agent re-instantiated per call (fresh system prompt with PKT datetime) — not a module-level singleton

**Acceptance criteria**:
- [ ] `AgentResponse` dataclass defined: `ticket_id`, `response_text`, `channel`, `escalated`, `escalation_id`, `resolution_status`, `error`
- [ ] `CustomerContext` dataclass defined: `customer_id`, `customer_name`, `customer_email`, `channel`, `message`, `conversation_id`
- [ ] `async def process_ticket(ctx: CustomerContext) -> AgentResponse` exists
- [ ] Agent is constructed inside `process_ticket()` with `build_system_prompt(ctx.channel, ctx.customer_name)` — NOT at module level
- [ ] Agent uses `model="gpt-4o-mini"`, `tools=[search_knowledge_base, create_ticket, get_customer_history, escalate_to_human, send_response, get_sentiment_trend, resolve_ticket]`
- [ ] `Runner.run(agent, ctx.message)` is awaited; `RunResult.final_output` extracted
- [ ] On `openai.APIError`: retry once; on second failure, attempt `escalate_to_human` (best-effort), return `AgentResponse(escalated=True, error=str(e))`
- [ ] `openai.AuthenticationError` and `openai.PermissionDeniedError` are NOT caught — these bubble up to the caller
- [ ] Conversation is created via `queries.create_conversation()` if `ctx.conversation_id` is None
- [ ] Customer is resolved via `queries.get_or_create_customer()` before building the prompt

---

### T-006: production/tests/test_agent_tools.py — Unit Tests (Mocked)

**Risk**: MEDIUM
**Dependencies**: T-001, T-004 (schemas.py, tools.py)
**Acceptance criteria**:
- [ ] Uses `pytest-asyncio` (`@pytest.mark.asyncio`) for all async test functions
- [ ] `asyncpg.Pool` mocked via `pytest-mock` `AsyncMock` — no live DB required
- [ ] `_get_openai_client()` patched to return a mock client for `search_knowledge_base` tests
- [ ] 3 test cases per tool (happy path, empty result, error/exception) = 21 tests minimum
- [ ] `search_knowledge_base` tests: valid query returns results; empty query raises Pydantic `ValidationError`; DB error returns `{"error": "...", "tool": "search_knowledge_base"}`
- [ ] `create_ticket` tests: valid input returns `ticket_id`; missing `customer_id` raises `ValidationError`; DB error returns error JSON
- [ ] `escalate_to_human` tests: valid escalation returns `escalation_id`; non-empty reason validation; idempotent re-escalation
- [ ] `send_response` tests: message truncated at channel limit; stub delivery returns `"stub_delivered"`; missing `ticket_id` raises `ValidationError`
- [ ] `resolve_ticket` tests: valid resolution; idempotent resolve; escalated ticket returns error JSON
- [ ] `get_sentiment_trend` tests: trend computation (improving/stable/deteriorating); empty history; recommend_escalation when avg < 0.3
- [ ] All tests pass without `OPENAI_API_KEY` or `DATABASE_URL` set

---

### T-007: production/tests/test_agent_integration.py — Integration Tests

**Risk**: MEDIUM
**Dependencies**: T-005, T-006 (all agent files)
**Acceptance criteria**:
- [ ] `pytestmark = pytest.mark.skipif(not os.environ.get("TEST_DATABASE_URL"), ...)` guard — skip gracefully without live DB
- [ ] `TestNewCustomerFlow`: full `process_ticket()` run → verify `AgentResponse.ticket_id` non-null, `resolution_status` in `{"pending", "resolved"}`
- [ ] `TestReturningCustomerCrossChannel`: customer with prior conversation history → verify acknowledgment in `response_text`
- [ ] `TestSentimentEscalation`: mock `get_sentiment_trend` returning [0.2, 0.1, 0.25] → verify `AgentResponse.escalated = True`
- [ ] `TestAllEscalationTriggers`: 8 synthetic cases (one per trigger) → `escalated = True` for each
- [ ] `TestAPIErrorRetry`: mock `Runner.run()` to raise `openai.APIError` twice → `escalated = True`, `error` populated
- [ ] `TestChannelFormatting`: verify `response_text` meets length limit for each channel
- [ ] `TestToolCallOrdering`: parse RunResult trace → `create_ticket` call appears before `send_response` call

---

## Risk Assessment Summary

| Task | Risk | Primary Risk Factor | Mitigation |
|------|------|---------------------|-----------|
| T-001 schemas.py | LOW | — | Straightforward Pydantic models |
| T-002 prompts.py | LOW | — | Port from working prototype |
| T-003 formatters.py | LOW | — | Port from working prototype; update limits |
| T-004 tools.py | **HIGH** | async asyncpg + OpenAI embeddings inside @function_tool; error JSON contract | Implement + unit-test each tool individually before wiring into agent |
| T-005 customer_success_agent.py | **HIGH** | LLM tool-call ordering; API retry; AgentResponse extraction from RunResult string | Test ordering via RunResult trace inspection; mock retry in T-007 |
| T-006 test_agent_tools.py | MEDIUM | AsyncMock for asyncpg Pool; mock OpenAI client | Use `pytest-asyncio` + `pytest-mock`; patch at module level |
| T-007 test_agent_integration.py | MEDIUM | Live DB + OpenAI API both required for full run | Skip guard; mock runner for ordering tests; live DB only for DB-round-trip tests |

**Recommended implementation order**: T-001 → T-002 → T-003 → T-006 (unit scaffolding) → T-004 → T-005 → T-007

---

## Dependencies Between Tasks

```
T-001 (schemas.py)
    └─► T-004 (tools.py) ────────────┐
T-002 (prompts.py)                   ├─► T-005 (agent.py) ──► T-007 (integration)
T-003 (formatters.py) ───────────────┘         │
                                               └─► T-006 (unit tests — partial)
T-004 (tools.py) ──────────────────────────────► T-006 (unit tests — full)
```

---

## Phase 1 Artifacts Generated

| Artifact | Path | Status |
|----------|------|--------|
| Research | `specs/006-production-agent/research.md` | ✅ Complete |
| Data Model | `specs/006-production-agent/data-model.md` | ✅ Complete |
| Tool Contracts | `specs/006-production-agent/contracts/tools.md` | ✅ Complete |
| Quickstart | `specs/006-production-agent/quickstart.md` | ✅ Complete |

---

## Next Step

Run `/sp.tasks` to generate `specs/006-production-agent/tasks.md` with
testable, dependency-ordered tasks derived from T-001 through T-007 above.
