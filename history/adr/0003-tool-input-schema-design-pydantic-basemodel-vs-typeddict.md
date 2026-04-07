# ADR-0003: Tool Input Schema Design — Pydantic BaseModel vs TypedDict

- **Status:** Accepted
- **Date:** 2026-04-04
- **Feature:** 006-production-agent (Phase 4B — OpenAI Agents SDK Agent)
- **Context:** Phase 4B implements 7 `@function_tool`-decorated functions for the production
  `CustomerSuccessAgent`. Each tool accepts structured inputs (e.g., `customer_id`, `ticket_id`,
  `channel`, `query`). The OpenAI Agents SDK supports two input schema approaches: `TypedDict`
  (lightweight, no runtime validation) and `Pydantic BaseModel` (runtime validation, Field
  constraints, auto-generated JSON Schema). The choice affects validation depth, testability,
  OpenAI SDK compatibility, and the complexity of all 7 tool definitions across
  `production/agent/customer_success_agent.py`. This decision is cross-cutting — all 7 tools
  must use the same pattern to maintain consistency and avoid mixed validation behaviour.

<!-- Significance checklist
     1) Impact: Yes — all 7 production tools, validation behaviour, test harness design
     2) Alternatives: Yes — TypedDict, Pydantic BaseModel, Annotated primitives (3 options)
     3) Scope: Yes — cross-cutting across the entire agent tool layer -->

## Decision

**Chosen approach: Pydantic `BaseModel` for tools with multiple or constrained inputs; `Annotated[T, Field(...)]` primitives for single-parameter tools.**

Concretely:

- Tools with 3+ parameters or requiring validation constraints use a dedicated Pydantic input model:

  ```python
  from pydantic import BaseModel, Field
  from agents import function_tool

  class SearchKBInput(BaseModel):
      query: str = Field(..., description="Customer question or topic", max_length=500)
      limit: int = Field(default=5, ge=1, le=20, description="Max results to return")

  @function_tool
  async def search_knowledge_base(params: SearchKBInput) -> str: ...

  class CreateTicketInput(BaseModel):
      customer_id: str = Field(..., description="Customer UUID from get_or_create_customer")
      conversation_id: str = Field(..., description="Conversation UUID")
      channel: str = Field(..., description="One of: email, whatsapp, web_form")
      subject: str | None = Field(default=None, description="Ticket subject line")
      category: str | None = Field(default=None, description="Support category")

  @function_tool
  async def create_ticket(params: CreateTicketInput) -> str: ...
  ```

- Tools with a single string input use `Annotated` primitives directly (simpler, avoids a wrapper class for a trivial schema):

  ```python
  from typing import Annotated
  from pydantic import Field

  @function_tool
  async def get_customer_history(
      customer_id: Annotated[str, Field(description="Customer UUID")],
      limit: int = 20,
  ) -> str: ...
  ```

- Tool mapping to the 7 production tools:

  | Tool | Schema approach | Reason |
  |------|----------------|--------|
  | `search_knowledge_base` | `SearchKBInput` BaseModel | query max_length + limit range constraints |
  | `create_ticket` | `CreateTicketInput` BaseModel | 5 params, channel enum validation |
  | `get_customer_history` | `Annotated` primitives | 2 params, no non-trivial constraints |
  | `escalate_to_human` | `EscalateInput` BaseModel | urgency enum + non-empty reason validation |
  | `send_response` | `SendResponseInput` BaseModel | channel enum + message non-empty constraint |
  | `get_sentiment_trend` | `Annotated` primitives | 2 params, no non-trivial constraints |
  | `resolve_ticket` | `ResolveTicketInput` BaseModel | non-empty resolution_summary constraint |

## Consequences

### Positive

- **Runtime validation at tool boundary**: Pydantic raises `ValidationError` before any database
  call for malformed inputs (e.g., `limit=0`, empty `reason`, invalid `channel` value). This
  prevents error-masking at the database layer and produces clear error messages.
- **Auto-generated JSON Schema**: The OpenAI Agents SDK reads Pydantic field descriptions and
  constraints to build the tool's JSON Schema used in the LLM function-calling prompt. This means
  field descriptions (e.g., `"One of: email, whatsapp, web_form"`) appear directly in the schema
  the model sees — improving model compliance with valid input values.
- **Test clarity**: Unit tests can construct input models directly (`SearchKBInput(query="...",
  limit=5)`) and assert validation errors with `pytest.raises(ValidationError)`, making boundary
  testing explicit and self-documenting.
- **ADR-0001 consistency**: The injectable pool pattern (ADR-0001) uses `asyncpg.Pool` as a
  typed parameter; Pydantic BaseModel approach is consistent with the project's preference for
  explicit typing and validation at boundaries.
- **SDK compatibility confirmed**: Context7 (`/openai/openai-agents-python`, v0.7.0) confirms
  that `@function_tool` with Pydantic `BaseModel` and `Annotated[T, Field(...)]` are both
  first-class supported patterns with `include_input_schema=True` producing valid nested schemas.

### Negative

- **Boilerplate for simple tools**: Tools with 1–2 unconstrained parameters do not benefit from
  a full BaseModel class. For these (`get_customer_history`, `get_sentiment_trend`), the
  `Annotated` primitive approach is used instead to avoid unnecessary wrapper classes.
- **Import surface**: `from pydantic import BaseModel, Field` is added to the agent module.
  The project already depends on Pydantic v2 (FastAPI dependency) — no new dependency introduced.
- **Schema explosion risk**: If future tools grow to 8+ parameters, BaseModel classes accumulate
  in the agent file. Mitigation: move input models to `production/agent/schemas.py` if the file
  exceeds ~300 lines.

## Alternatives Considered

### Alternative A — TypedDict for all tool inputs

```python
from typing import TypedDict

class SearchKBInput(TypedDict):
    query: str
    limit: int

@function_tool
async def search_knowledge_base(params: SearchKBInput) -> str: ...
```

**Rejected because:**
- No runtime validation — `SearchKBInput(query="", limit=0)` passes silently and reaches the
  database layer before failing on a pgvector query with an empty embedding.
- `Field` constraints (`max_length`, `ge`, `le`, enum literals) are not supported by TypedDict.
  These constraints cannot be expressed or enforced at the tool boundary.
- TypedDict produces a weaker JSON Schema (no descriptions, no constraints) — the LLM sees less
  guidance about valid input values, increasing the probability of invalid tool calls.
- Confirmed via Context7: TypedDict generates a basic object schema without Field metadata.

### Alternative B — Plain positional parameters with no schema wrapper

```python
@function_tool
async def create_ticket(
    customer_id: str,
    conversation_id: str,
    channel: str,
    subject: str | None = None,
    category: str | None = None,
) -> str: ...
```

**Rejected because:**
- The SDK auto-generates a JSON Schema from positional parameters, but Field descriptions are
  lost. The LLM cannot distinguish `"One of: email, whatsapp, web_form"` from a free-form string.
- Validation is still absent at runtime — `channel="sms"` would silently reach the database.
- For tools with 4–5 parameters, the function signature becomes visually noisy and harder to
  test (must call with keyword arguments; cannot snapshot the input as a typed object).
- Acceptable only for single-parameter tools; chosen for `get_customer_history` and
  `get_sentiment_trend` via `Annotated` primitives as a middle ground.

### Alternative C — Single dict input for all tools

```python
@function_tool
async def create_ticket(params: dict) -> str: ...
```

**Rejected because:**
- Completely untyped — no JSON Schema generated. The LLM receives no guidance on expected keys
  or values. This is the worst option for model compliance.
- No IDE support, no runtime validation, no test assertions. Ruled out immediately.

## References

- Feature Spec: `specs/006-production-agent/spec.md` (FR-010 through FR-029, tool input/output contracts)
- Implementation Plan: `specs/006-production-agent/plan.md` (pending — to be generated by /sp.plan)
- Related ADRs:
  - ADR-0001: ConversationStore Lifecycle — injectable pool pattern (same validation-at-boundary philosophy)
  - ADR-0002: Skill Pipeline synchronous design — establishes tool call ordering context
- Context7 Evidence: `/openai/openai-agents-python` v0.7.0 — `@function_tool` with Pydantic BaseModel and Annotated[T, Field()] confirmed as first-class supported patterns
