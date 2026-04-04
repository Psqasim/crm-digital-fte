# Research: Phase 4B — Production Agent

**Branch**: `006-production-agent` | **Date**: 2026-04-04
**Phase**: Phase 0 output for `/sp.plan`

All unknowns from the Technical Context resolved below.

---

## R-001: Async @function_tool with asyncpg Pool

**Unknown**: Can `@function_tool` decorate an `async def` function that awaits asyncpg calls?
Does the OpenAI Agents SDK Runner propagate the event loop through tool execution?

**Decision**: Yes — fully supported. `@function_tool` works on both sync and async functions.
When `Runner.run()` is awaited, it runs inside the caller's event loop and correctly awaits
async tool coroutines.

**Rationale**: Context7 (`/openai/openai-agents-python` v0.7.0) confirms async tools in multiple
examples. The SDK `Runner` uses `asyncio` internally and simply `await`s any tool that is a
coroutine. No special wrapping required.

**Pattern**:
```python
@function_tool
async def create_ticket(params: CreateTicketInput) -> str:
    pool = await get_db_pool()                  # awaited — safe inside Runner
    ticket_id = await queries.create_ticket(    # asyncpg call — safe
        pool, params.customer_id, ...
    )
    return json.dumps({"ticket_id": ticket_id})
```

**Alternatives considered**:
- Sync wrapper with `asyncio.run()` — rejected: nests event loops, crashes if Runner already holds an event loop
- `RunContextWrapper` context injection — valid alternative; deferred to future refactor if pool management grows complex

---

## R-002: OpenAI Embedding Inside @function_tool

**Unknown**: How to call `openai.AsyncOpenAI().embeddings.create()` inside `search_knowledge_base`
without creating a new client per call?

**Decision**: Module-level `AsyncOpenAI` client, lazily initialised, reused across all tool calls.

**Rationale**: Creating a new `AsyncOpenAI()` per tool call is safe but wasteful. A module-level
singleton avoids repeated HTTPX connection setup and matches the pool singleton pattern from
ADR-0001.

**Pattern**:
```python
# production/agent/tools.py
import openai

_openai_client: openai.AsyncOpenAI | None = None

def _get_openai_client() -> openai.AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = openai.AsyncOpenAI()  # reads OPENAI_API_KEY from env
    return _openai_client

@function_tool
async def search_knowledge_base(params: SearchKBInput) -> str:
    client = _get_openai_client()
    embed_resp = await client.embeddings.create(
        model="text-embedding-3-small",
        input=params.query,
    )
    embedding = embed_resp.data[0].embedding   # list[float], 1536 dims
    pool = await get_db_pool()
    results = await queries.search_knowledge_base(pool, embedding, params.limit)
    return json.dumps(results)
```

**Alternatives considered**:
- Per-call client: safe but slower
- RunContextWrapper injection: cleaner but requires changing tool signatures — deferred to Phase 5 refactor

---

## R-003: Tool Call Ordering Enforcement

**Unknown**: The spec requires `create_ticket` BEFORE `send_response`. Can this be enforced
in code, or only via system prompt instructions?

**Decision**: Enforce via system prompt instructions (ALWAYS rules). Supplement with a
`ticket_id` required parameter on `send_response` — the agent cannot call `send_response`
without having the ticket_id from `create_ticket` first.

**Rationale**: The OpenAI Agents SDK does not support programmatic tool call ordering
(i.e., no `precondition=` parameter). However, making `send_response` require `ticket_id`
as a non-optional input creates a natural data dependency: the agent must call `create_ticket`
first (which returns `ticket_id`) to have the value available for `send_response`. This is a
structural enforcement, not just a guideline.

**Pattern**: `send_response` schema:
```python
class SendResponseInput(BaseModel):
    ticket_id: str = Field(..., description="UUID from create_ticket — call create_ticket first")
    message: str = Field(..., min_length=1)
    channel: str = Field(..., description="email | whatsapp | web_form")
```

---

## R-004: AgentResponse Extraction from Runner Result

**Unknown**: How does `Runner.run()` return the final output? What type is `RunResult.final_output`?

**Decision**: `RunResult.final_output` is a `str` — the last text message produced by the agent.
`process_ticket()` builds an `AgentResponse` dataclass from this string plus metadata.

**Rationale**: Context7 shows `result.final_output` is always a string. The production
`process_ticket()` wraps `Runner.run()`, catches `openai.APIError` for retry, and constructs
the `AgentResponse` from the final output string plus the ticket_id and other metadata tracked
during the run.

---

## R-005: Retry Strategy for OpenAI API Errors

**Unknown**: What exception types should be caught for the one-retry policy?

**Decision**: Catch `openai.APIError` (base class covering `APIConnectionError`,
`APITimeoutError`, `RateLimitError`, `InternalServerError`). Retry once. If second attempt
also raises, call `escalate_to_human` with `reason="api_error"` and return `AgentResponse`
with `escalated=True, error=str(e)`.

**Rationale**: `openai.APIError` is the documented base class for all retriable errors in the
OpenAI Python SDK. `openai.AuthenticationError` and `openai.PermissionDeniedError` are NOT
caught — these indicate misconfiguration and should surface as errors to the operator, not
be swallowed via escalation.
