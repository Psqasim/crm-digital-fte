# Implementation Plan: MCP Server — CRM Tool Gateway

**Branch**: `003-mcp-server` | **Date**: 2026-04-02 | **Spec**: `specs/003-mcp-server/spec.md`
**Input**: Feature specification from `/specs/003-mcp-server/spec.md`

---

## Summary

Build a FastMCP stdio server at `src/mcp_server/server.py` that exposes the NexaFlow agent's
7 capabilities as MCP tools. The server is a **thin adapter only** — all business logic stays
in the existing Phase 2B/2C modules. Tools wrap `KnowledgeBase`, `ConversationStore`, and
`EscalationEvaluator` via direct function calls; no new business logic is introduced.

Transport: `stdio` (standard for Claude Code / Claude Desktop MCP integration — no port).
Dependency: `mcp>=1.2.0` added to `requirements.txt`.

---

## Technical Context

**Language/Version**: Python 3.12  
**Primary Dependencies**: `mcp>=1.2.0` (FastMCP), `openai>=1.0`, `python-dotenv>=1.0.0`  
**Storage**: In-memory `ConversationStore` singleton (Phase 2C) — no new persistence  
**Testing**: `pytest>=8.0.0` — direct function import strategy (no MCP client required)  
**Target Platform**: Linux (WSL2) — local development; `stdio` transport only  
**Project Type**: Single Python project  
**Performance Goals**: Tool call response <5 seconds (SC-002); server startup <3 seconds (SC-005)  
**Constraints**: No port assignment (stdio has none); must not conflict with future FastAPI port 8000  
**Scale/Scope**: Single-process, single-threaded; ~800 tickets/week; Phase 2D only

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| III-1 Kafka ingestion | DEFERRED (by design) | MCP server is Phase 2D prototype; Kafka deferred to Phase 4 |
| III-2 Customer identity unification | PASS | MCP `create_ticket` uses `store.resolve_identity()` — email as primary key |
| III-3 Channel metadata preservation | PASS | `create_ticket` requires `channel` param; stored in ConversationStore |
| IV-2 create_ticket first | PASS | Tool order enforced by agent caller, not server |
| IV-1 Datetime injection | PASS | `send_response` records PKT timestamp; `escalate_to_human` records UTC timestamp |
| VI Technology stack | PASS | FastMCP (official `mcp` package); no LangChain, no raw sockets |
| Secrets policy | PASS | OpenAI key via `.env`; server fails gracefully if missing (SC-004 edge case) |

**Gate result: PASS** — no constitution violations. Kafka deferral is pre-approved in spec Assumptions.

---

## Project Structure

### Documentation (this feature)

```text
specs/003-mcp-server/
├── plan.md              ← this file
├── research.md          ← Phase 0 output (MCP SDK patterns, tool mapping)
├── data-model.md        ← Phase 1 output (entities, ticket index, response shapes)
├── contracts/
│   └── tool_schemas.md  ← Phase 1 output (per-tool input/output contracts)
├── quickstart.md        ← Phase 1 output (how to run and test the server)
└── tasks.md             ← Phase 2 output (sp.tasks — NOT created here)
```

### Source Code

```text
src/
├── agent/               ← existing Phase 2B/2C modules (DO NOT MODIFY)
│   ├── models.py
│   ├── knowledge_base.py
│   ├── conversation_store.py
│   ├── escalation_evaluator.py
│   ├── channel_formatter.py
│   ├── prompts.py
│   └── prototype.py
└── mcp_server/          ← NEW (Phase 2D)
    ├── __init__.py
    └── server.py        ← FastMCP server with all 7 tools

tests/
├── unit/
│   ├── test_conversation_store.py   ← existing (Phase 2C)
│   └── mcp_server/                  ← NEW (Phase 2D)
│       ├── __init__.py
│       └── test_tools.py            ← direct-import tool tests
├── test_core_loop.py                ← existing
├── test_cross_channel.py            ← existing
├── test_escalation_evaluator.py     ← existing
└── test_prototype.py                ← existing
```

**Structure Decision**: Single project; MCP server is a sibling package to `src/agent/`. No new
top-level directories. All 52 existing tests remain intact (SC-006 invariant).

---

## Complexity Tracking

No constitution violations requiring justification for this feature.

---

## Phase 0: Research Findings

*See `specs/003-mcp-server/research.md` for full detail. Summary below.*

### Decision 1 — FastMCP over low-level `mcp.server.Server`

**Decision**: Use `from mcp.server.fastmcp import FastMCP`  
**Rationale**: FastMCP is the official high-level API bundled in the `mcp` Python SDK (≥1.2.0).
It generates tool schemas automatically from Python type hints and docstrings — zero boilerplate.
The `@mcp.tool()` decorator pattern matches what spec FR-009 requires (human-readable description
+ parameter schema auto-generated).  
**Alternatives considered**: Low-level `mcp.server.Server` with manual `ListToolsResult` /
`CallToolResult` — rejected as significantly more code for no gain in this wrapper use-case.

### Decision 2 — stdio transport only

**Decision**: `mcp.run(transport="stdio")`  
**Rationale**: Claude Code MCP integration uses stdio. Phase 2D is local development only.
HTTP/SSE is explicitly out of scope (spec Out of Scope section).  
**Port conflict**: N/A — stdio has no port. Future FastAPI on port 8000 is fully independent.

### Decision 3 — Direct-import test strategy

**Decision**: Test tool logic by importing `server.py` functions directly in pytest; do NOT
require a running MCP client or subprocess for unit tests.  
**Rationale**: The `@mcp.tool()` decorator does not hide the underlying Python function — it
remains callable as a normal coroutine. Tests call `await search_knowledge_base("query")` etc.
directly. `reset_store()` provides clean state between tests.  
**Alternatives considered**: `mcp.dev` interactive inspector — useful for manual smoke testing
but not automatable; `mcp.client.stdio` subprocess — overkill for unit tests, added in
integration test layer later.

### Decision 4 — Ticket index adapter dict in server.py

**Decision**: `server.py` maintains a module-level `_ticket_index: dict[str, str]` mapping
`ticket_id → conversation_id`. This is NOT added to `ConversationStore` (no modification to
Phase 2C code).  
**Rationale**: `ConversationStore` addresses all operations via `conversation_id`. The MCP spec
exposes `ticket_id` as the public handle. The server layer must bridge this gap without
modifying the existing store.  
**Constraint**: The ticket index lives only as long as the server process (consistent with
in-memory store lifetime).

### Decision 5 — No stdout in stdio server

**Decision**: All logging in `server.py` uses `logging` module directed to stderr. `print()` is
NEVER used (would corrupt JSON-RPC on stdout).  
**Rationale**: MCP SDK documentation explicitly warns: "Never write to stdout. Writing to stdout
will corrupt the JSON-RPC messages."

### Decision 6 — Tools return `str` (not raw Python objects)

**Decision**: All 7 tools return `str` — either a JSON-serialised result dict or a plain error
message string. No raw dataclass/dict objects are returned.  
**Rationale**: FR-011 (structured, serialisable responses). The `@mcp.tool()` decorator with
return type `str` is the simplest, fully-compliant approach. `json.dumps()` serialises results.

### Decision 7 — Graceful OpenAI key absence

**Decision**: Server boots regardless of `OPENAI_API_KEY` presence. `escalate_to_human` calls
`evaluate_escalation()` only when AI is available; if unavailable, it transitions the ticket to
ESCALATED without calling the LLM (treats escalation request as authoritative from caller).  
**Rationale**: SC-004 — all tools return descriptive error results, not crashes. Edge case from
spec: "What happens when the OpenAI API key is missing at server start?"

---

## Phase 1: Design & Contracts

*See `specs/003-mcp-server/data-model.md` and `specs/003-mcp-server/contracts/tool_schemas.md`.*

### Tool-to-Module Mapping

| Tool | Wraps | Key call |
|------|-------|---------|
| `search_knowledge_base(query)` | `KnowledgeBase` | `_kb.search(query, top_k=3)` |
| `create_ticket(customer_id, issue, priority, channel)` | `ConversationStore` | `store.get_or_create_customer()` + `store.get_or_create_conversation()` |
| `get_customer_history(customer_id)` | `ConversationStore` | `store.get_customer()` + iterate `_conversations` |
| `escalate_to_human(ticket_id, reason)` | `ConversationStore` + `EscalationEvaluator` (optional) | `store.transition_ticket(conv_id, TicketStatus.ESCALATED)` |
| `send_response(ticket_id, message, channel)` | `ConversationStore` | `store.add_message()` (simulated delivery) |
| `get_sentiment_trend(customer_id)` | `ConversationStore` | `store.compute_sentiment_trend(conv)` |
| `resolve_ticket(ticket_id, resolution_summary)` | `ConversationStore` | `store.transition_ticket(conv_id, TicketStatus.RESOLVED)` |

### Server Initialisation Sequence

```
1. import KnowledgeBase → _kb = KnowledgeBase()      # loads context/product-docs.md
2. import get_store → store = get_store()             # singleton, shared with prototype
3. _ticket_index: dict[str, str] = {}                  # ticket_id → conversation_id
4. mcp = FastMCP("nexaflow-crm")
5. @mcp.tool() decorators register all 7 tools
6. def main(): mcp.run(transport="stdio")
7. if __name__ == "__main__": main()
```

### Error Handling Contract (all tools)

Every tool wraps its body in `try/except Exception as e` and returns a JSON error string on
failure. Pattern:

```python
try:
    # ... tool logic ...
    return json.dumps(result)
except Exception as e:
    logging.error("tool_name error: %s", e, exc_info=True)
    return json.dumps({"error": str(e), "tool": "tool_name"})
```

Validation errors (missing params, invalid channel, empty body) are caught before the try block
and returned early as:
```python
return json.dumps({"error": "validation: <reason>", "tool": "tool_name"})
```

### Priority Validation

Accepted values: `low`, `medium`, `high`, `critical` — matching `escalation_evaluator.py` urgency
vocabulary. Unknown priority → validation error returned.

### Channel Validation

Accepted values: `email`, `whatsapp`, `web_form` — matching `Channel` enum in `models.py`.
Unknown channel → validation error returned.

### State Transition Safety

`ConversationStore.Ticket.transition()` raises `ValueError` on invalid transitions. The MCP tool
layer catches this and returns it as a descriptive error string (idempotent / already-resolved
scenarios from spec scenarios 3 of User Stories 4 and 7).

---

## Test Strategy

### Scope

- **Unit tests** (`tests/unit/mcp_server/test_tools.py`): call each tool function directly
  as a coroutine; use `reset_store()` in `pytest.fixture(autouse=True)` for isolation.
- **Regression gate**: All 52 existing passing tests must continue to pass after MCP server
  is added (SC-006).
- **Manual smoke test**: `python -m src.mcp_server.server` then send JSON-RPC via stdin
  OR use `mcp dev src/mcp_server/server.py` if mcp CLI is installed.

### Coverage targets (Phase 2D)

| Test file | What it covers |
|-----------|---------------|
| `test_tools.py` | All 7 tools × happy path + at least 2 error/edge cases each = ~21 test functions |
| Existing 52 tests | Regression — must remain green |

### Key test cases required by spec

| Spec scenario | Test function |
|---------------|---------------|
| US1 SC1: search returns ranked results | `test_search_returns_ranked_results` |
| US1 SC2: no match → empty list, not error | `test_search_no_match_returns_empty` |
| US2 SC1: valid create_ticket returns ID | `test_create_ticket_returns_id` |
| US2 SC3: invalid channel → error | `test_create_ticket_invalid_channel` |
| US3 SC2: unknown customer → empty history | `test_history_unknown_customer` |
| US4 SC2: unknown ticket → not-found error | `test_escalate_unknown_ticket` |
| US5 SC2: unsupported channel → error | `test_send_response_invalid_channel` |
| US5 SC3: empty message → validation error | `test_send_response_empty_message` |
| US6 SC2: <3 interactions → insufficient data | `test_sentiment_insufficient_data` |
| US7 SC2: already resolved → idempotent | `test_resolve_already_resolved` |
| US7 SC3: empty summary → validation error | `test_resolve_empty_summary` |
| Edge: fresh store + all tools → no crash | `test_fresh_store_all_tools_no_crash` |

---

## Non-Functional Requirements

| NFR | Budget | How met |
|-----|--------|---------|
| Startup time | <3 s (SC-005) | KnowledgeBase loads one markdown file; no network call at boot |
| Tool call latency | <5 s (SC-002) | In-memory ops are <1 ms; only `escalate_to_human` may hit OpenAI |
| Port conflict | None (stdio) | `mcp.run(transport="stdio")` uses stdin/stdout; FastAPI on 8000 is independent |
| stdout purity | Zero non-JSON-RPC output | Logging directed to stderr; no `print()` statements |
| OpenAI key absent | Graceful degradation | `escalate_to_human` skips AI eval, escalates unconditionally |

---

## Follow-ups and Risks

1. **Ticket index is ephemeral**: `_ticket_index` in `server.py` is process-local. If the server
   restarts mid-session, previously created ticket IDs become unresolvable. Acceptable in Phase 2D
   (single-process, in-memory scope). Phase 4 PostgreSQL persistence resolves this permanently.

2. **ConversationStore.transition_ticket race**: The store is not thread-safe (documented in
   Phase 2C). Phase 2D is single-threaded (spec Assumption 5), so this is acceptable. Note in
   code comment for Phase 4 awareness.

3. **`mcp` package not yet in requirements.txt**: Must be added before `/sp.tasks` implementation.
   Task 1 in tasks.md must be `Add mcp>=1.2.0 to requirements.txt`.
