# Data Model: Phase 4B — Production Agent

**Branch**: `006-production-agent` | **Date**: 2026-04-04
**Phase**: Phase 1 output for `/sp.plan`

---

## Production Data Contracts

All types below are defined in `production/agent/` modules.
No database schema changes — Phase 4A tables are authoritative.

---

### AgentResponse (production/agent/customer_success_agent.py)

Extends prototype `src/agent/models.py::AgentResponse` with `escalation_id` field.

```
AgentResponse
├── ticket_id: str | None          # UUID from create_ticket; None if ticket creation failed
├── response_text: str             # Final formatted text sent to customer
├── channel: str                   # email | whatsapp | web_form
├── escalated: bool                # True if escalate_to_human was called
├── escalation_id: str | None      # UUID from escalation record; None if not escalated
├── resolution_status: str         # open | pending | resolved | escalated | error
└── error: str | None              # Populated if API retry failed; None otherwise
```

**State transitions**:
- Normal path: `open → pending → resolved` (create_ticket → send_response → resolve_ticket)
- Escalation path: `open → escalated` (create_ticket → escalate_to_human)
- Error path: `error` (API retry failed; escalation attempted)

---

### CustomerContext (production/agent/customer_success_agent.py)

Input bundle passed to `process_ticket()` on every invocation.

```
CustomerContext
├── customer_id: str               # UUID from get_or_create_customer
├── customer_name: str             # Full name (first name used in greetings)
├── customer_email: str            # Primary identifier
├── channel: str                   # email | whatsapp | web_form
├── message: str                   # Raw inbound message text
└── conversation_id: str | None    # UUID if existing; None triggers create_conversation
```

---

### FormattedResponse (production/agent/formatters.py)

Output of each channel formatter function.

```
FormattedResponse
├── formatted_text: str            # Final text after channel rules applied
├── channel: str                   # Echo of target channel
└── formatting_notes: list[str]    # Transformations applied (truncation, markdown strip, etc.)
```

---

### Pydantic Tool Input Models (production/agent/tools.py) — per ADR-0003

**SearchKBInput** — `search_knowledge_base`
```
SearchKBInput
├── query: str                     # max_length=500, non-empty
└── limit: int                     # default=5, ge=1, le=20
```

**CreateTicketInput** — `create_ticket`
```
CreateTicketInput
├── customer_id: str               # UUID from get_or_create_customer
├── conversation_id: str           # UUID from create_conversation
├── channel: str                   # email | whatsapp | web_form
├── subject: str | None            # default=None
└── category: str | None           # default=None
```

**EscalateInput** — `escalate_to_human`
```
EscalateInput
├── ticket_id: str                 # UUID from create_ticket
├── reason: str                    # min_length=1, non-empty
└── urgency: str                   # default="medium"; low|medium|high|critical
```

**SendResponseInput** — `send_response`
```
SendResponseInput
├── ticket_id: str                 # UUID — structural dependency on create_ticket
├── message: str                   # min_length=1, non-empty
└── channel: str                   # email | whatsapp | web_form
```

**ResolveTicketInput** — `resolve_ticket`
```
ResolveTicketInput
├── ticket_id: str                 # UUID from create_ticket
└── resolution_summary: str        # min_length=1, non-empty
```

**Simple tools (Annotated primitives, no BaseModel)** — per ADR-0003:
- `get_customer_history(customer_id: str, limit: int = 20)`
- `get_sentiment_trend(customer_id: str, last_n: int = 5)`

---

### Formatter Constants (production/agent/formatters.py)

Ported from `src/agent/channel_formatter.py` — limits tightened per spec §8:

| Constant | Value | Rule |
|----------|-------|------|
| `EMAIL_HARD_LIMIT_WORDS` | 500 words | spec FR-021, NEVER-6 |
| `WHATSAPP_HARD_LIMIT_CHARS` | 1600 chars | spec FR-021, NEVER-6 |
| `WHATSAPP_SOFT_LIMIT_CHARS` | 250 chars | prompts.py instruction |
| `WEBFORM_HARD_LIMIT_CHARS` | 1000 chars | spec FR-021, NEVER-6 |
| `NEXAFLOW_SIGNATURE` | 3-line block | email only |

---

### Tool Return Types (JSON strings)

All tools return `str` (JSON-encoded). The agent deserialises internally.

| Tool | Success payload | Error payload |
|------|----------------|---------------|
| `search_knowledge_base` | `{"results": [...], "count": N}` | `{"error": "...", "tool": "search_knowledge_base"}` |
| `create_ticket` | `{"ticket_id": "...", "status": "open", ...}` | `{"error": "...", "tool": "create_ticket"}` |
| `get_customer_history` | `{"conversations": [...], "count": N}` | `[]` (empty, not error) |
| `escalate_to_human` | `{"escalation_id": "...", "status": "escalated", ...}` | `{"error": "...", "tool": "escalate_to_human"}` |
| `send_response` | `{"delivery_status": "stub_delivered", ...}` | `{"error": "...", "tool": "send_response"}` |
| `get_sentiment_trend` | `{"scores": [...], "count": N}` | `[]` (empty, not error) |
| `resolve_ticket` | `{"ticket_id": "...", "status": "resolved", ...}` | `{"error": "...", "tool": "resolve_ticket"}` |
