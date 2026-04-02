# Tool Schemas: Phase 2D — MCP Server

**Date**: 2026-04-02 | **Branch**: `003-mcp-server`

All 7 tools exposed by `src/mcp_server/server.py`. Each entry documents:
- Python function signature (as registered via `@mcp.tool()`)
- Input constraints
- Success return shape (JSON string)
- Error return shape (JSON string)
- Underlying module call

---

## Tool 1 — `search_knowledge_base`

**FR**: FR-002

```python
@mcp.tool()
async def search_knowledge_base(query: str) -> str:
    """Search NexaFlow product documentation for relevant information.

    Args:
        query: The search query. Use natural language describing the customer's issue.
    """
```

| Parameter | Type | Required | Constraints |
|-----------|------|----------|-------------|
| `query` | `str` | yes | non-empty |

**Underlying call**: `_kb.search(query, top_k=3)` — returns `list[KBResult]`

**Success**:
```json
{"results": [{"section_title":"...", "content":"...", "relevance_score": 0.42}], "count": 3, "query": "..."}
```

**Empty result** (no match): `{"results": [], "count": 0, "query": "..."}`

**Error**: `{"error": "validation: query must not be empty", "tool": "search_knowledge_base"}`

---

## Tool 2 — `create_ticket`

**FR**: FR-003

```python
@mcp.tool()
async def create_ticket(
    customer_id: str,
    issue: str,
    priority: str,
    channel: str,
) -> str:
    """Create a new support ticket for a customer.

    Args:
        customer_id: Customer email address (primary key) or phone:+1234567890 for WhatsApp.
        issue: Description of the customer's issue (used as conversation topic).
        priority: Ticket priority. One of: low, medium, high, critical.
        channel: Originating channel. One of: email, whatsapp, web_form.
    """
```

| Parameter | Type | Required | Constraints |
|-----------|------|----------|-------------|
| `customer_id` | `str` | yes | non-empty |
| `issue` | `str` | yes | non-empty |
| `priority` | `str` | yes | `low \| medium \| high \| critical` |
| `channel` | `str` | yes | `email \| whatsapp \| web_form` |

**Underlying calls**:
1. `store.get_or_create_customer(key=customer_id, name=customer_id, channel=channel)`
2. `store.get_or_create_conversation(customer_key=customer_id, channel=channel)`
3. `store.add_topic(conv.id, issue[:100])` — truncated to 100 chars
4. `_ticket_index[ticket_id] = conv.id`

**Success**: `{"ticket_id":"TKT-a1b2c3d4", "customer_id":"...", "status":"open", "channel":"...", "created_at":"..."}`

**Error examples**:
- `{"error": "validation: priority must be one of: low, medium, high, critical", "tool": "create_ticket"}`
- `{"error": "validation: channel must be one of: email, whatsapp, web_form", "tool": "create_ticket"}`

---

## Tool 3 — `get_customer_history`

**FR**: FR-004

```python
@mcp.tool()
async def get_customer_history(customer_id: str) -> str:
    """Retrieve full interaction history for a customer across all channels.

    Args:
        customer_id: Customer email address or phone:+1234567890.
    """
```

| Parameter | Type | Required | Constraints |
|-----------|------|----------|-------------|
| `customer_id` | `str` | yes | non-empty |

**Underlying calls**:
1. `store.get_customer(customer_id)` — returns `CustomerProfile | None`
2. For each `conv_id` in `profile.conversation_ids`: fetch `_conversations[conv_id]`

**Success**: Full history object (see `data-model.md`)

**Unknown customer**: `{"customer_id":"...", "name":null, "channels_used":[], "conversation_count":0, "conversations":[]}`

**Error**: `{"error": "validation: customer_id must not be empty", "tool": "get_customer_history"}`

---

## Tool 4 — `escalate_to_human`

**FR**: FR-005

```python
@mcp.tool()
async def escalate_to_human(ticket_id: str, reason: str) -> str:
    """Escalate a support ticket to a human agent.

    Args:
        ticket_id: The ticket identifier returned by create_ticket (e.g. TKT-a1b2c3d4).
        reason: Human-readable reason for escalation (e.g. "customer requested human agent").
    """
```

| Parameter | Type | Required | Constraints |
|-----------|------|----------|-------------|
| `ticket_id` | `str` | yes | must exist in `_ticket_index` |
| `reason` | `str` | yes | non-empty |

**Underlying calls**:
1. Lookup `conv_id = _ticket_index.get(ticket_id)` — if missing → not-found error
2. `store.transition_ticket(conv_id, TicketStatus.ESCALATED)` — catches `ValueError` for invalid transitions
3. Returns `ESC-{uuid.hex8}` escalation ID

**Success**: `{"escalation_id":"ESC-...", "ticket_id":"...", "status":"escalated", "reason":"...", "escalated_at":"..."}`

**Not found**: `{"error": "ticket TKT-xyz not found", "tool": "escalate_to_human"}`

**Already terminal**: `{"error": "invalid transition: resolved → escalated", "tool": "escalate_to_human"}`

---

## Tool 5 — `send_response`

**FR**: FR-006

```python
@mcp.tool()
async def send_response(ticket_id: str, message: str, channel: str) -> str:
    """Send a response message to a customer through a specific channel.

    Delivery is simulated (logged to stderr) in Phase 2D.
    Real channel dispatch (Gmail, Twilio) is deferred to Phase 4.

    Args:
        ticket_id: The ticket identifier returned by create_ticket.
        message: The response message body to send to the customer.
        channel: Delivery channel. One of: email, whatsapp, web_form.
    """
```

| Parameter | Type | Required | Constraints |
|-----------|------|----------|-------------|
| `ticket_id` | `str` | yes | must exist in `_ticket_index` |
| `message` | `str` | yes | non-empty |
| `channel` | `str` | yes | `email \| whatsapp \| web_form` |

**Underlying calls**:
1. Validate `channel` against `Channel` enum — error if invalid
2. Validate `message` is non-empty — validation error if empty
3. Lookup `conv_id = _ticket_index.get(ticket_id)` — if missing → not-found error
4. `store.add_message(conv_id, Message(direction="outbound", ...))` — records delivery
5. Log to stderr: `"[SIMULATED SEND] channel={channel} ticket={ticket_id} len={len(message)}"`

**Success**: `{"delivery_status":"delivered", "ticket_id":"...", "channel":"...", "message_length":120, "timestamp":"..."}`

**Validation errors**:
- `{"error": "validation: message must not be empty", "tool": "send_response"}`
- `{"error": "validation: channel must be one of: email, whatsapp, web_form", "tool": "send_response"}`
- `{"error": "ticket TKT-xyz not found", "tool": "send_response"}`

---

## Tool 6 — `get_sentiment_trend`

**FR**: FR-007

```python
@mcp.tool()
async def get_sentiment_trend(customer_id: str) -> str:
    """Analyse sentiment trend for a customer based on recent interactions.

    Returns a trend label (improving/stable/deteriorating) and escalation recommendation.

    Args:
        customer_id: Customer email address or phone:+1234567890.
    """
```

| Parameter | Type | Required | Constraints |
|-----------|------|----------|-------------|
| `customer_id` | `str` | yes | non-empty |

**Underlying calls**:
1. `store.get_customer(customer_id)` — if not found → no-history response
2. `store.get_active_conversation(customer_id)` — if none → look at most recent conversation
3. `store.compute_sentiment_trend(conv)` — returns `SentimentTrend`

**Insufficient data** (< 2 inbound messages with scores):
```json
{"customer_id":"...", "trend":"stable", "window_scores":[], "window_size":3, "recommend_escalation":false, "note":"insufficient data"}
```

**Success**:
```json
{"customer_id":"...", "trend":"deteriorating", "window_scores":[0.7,0.4,0.2], "window_size":3, "recommend_escalation":true}
```

`recommend_escalation` is `true` when `trend == "deteriorating"`.

---

## Tool 7 — `resolve_ticket`

**FR**: FR-008

```python
@mcp.tool()
async def resolve_ticket(ticket_id: str, resolution_summary: str) -> str:
    """Mark a support ticket as resolved with a resolution summary.

    Args:
        ticket_id: The ticket identifier returned by create_ticket.
        resolution_summary: A brief description of how the issue was resolved.
    """
```

| Parameter | Type | Required | Constraints |
|-----------|------|----------|-------------|
| `ticket_id` | `str` | yes | must exist in `_ticket_index` |
| `resolution_summary` | `str` | yes | non-empty |

**Underlying calls**:
1. Validate `resolution_summary` non-empty — validation error if empty
2. Lookup `conv_id = _ticket_index.get(ticket_id)` — if missing → not-found error
3. `conv = _conversations[conv_id]` — get current status
4. If already RESOLVED: return idempotent success (no state change)
5. Else: `store.transition_ticket(conv_id, TicketStatus.RESOLVED)`
6. Store summary via `store.add_topic(conv_id, f"resolved:{resolution_summary[:100]}")`

**Success**: `{"ticket_id":"...", "status":"resolved", "resolution_summary":"...", "resolved_at":"..."}`

**Already resolved** (idempotent):
```json
{"ticket_id":"...", "status":"resolved", "note":"ticket was already resolved", "resolved_at":"..."}
```

**Validation error**: `{"error": "validation: resolution_summary must not be empty", "tool": "resolve_ticket"}`

**Not found**: `{"error": "ticket TKT-xyz not found", "tool": "resolve_ticket"}`

---

## Summary Table

| # | Tool | FR | Module | Can fail w/o OpenAI? |
|---|------|----|--------|---------------------|
| 1 | `search_knowledge_base` | FR-002 | `KnowledgeBase` | Yes — no OpenAI needed |
| 2 | `create_ticket` | FR-003 | `ConversationStore` | Yes — no OpenAI needed |
| 3 | `get_customer_history` | FR-004 | `ConversationStore` | Yes — no OpenAI needed |
| 4 | `escalate_to_human` | FR-005 | `ConversationStore` | Yes — degrades gracefully |
| 5 | `send_response` | FR-006 | `ConversationStore` | Yes — no OpenAI needed |
| 6 | `get_sentiment_trend` | FR-007 | `ConversationStore` | Yes — no OpenAI needed |
| 7 | `resolve_ticket` | FR-008 | `ConversationStore` | Yes — no OpenAI needed |
