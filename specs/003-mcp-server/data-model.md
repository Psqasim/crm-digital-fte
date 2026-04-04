# Data Model: Phase 2D — MCP Server

**Date**: 2026-04-02 | **Branch**: `003-mcp-server`

---

## Overview

Phase 2D introduces **no new persistent entities**. All state resides in the existing
`ConversationStore` singleton from Phase 2C. The MCP server layer adds one lightweight
in-process adapter structure.

---

## Existing Entities (read/write via MCP tools)

### Ticket (inside `Conversation`)
Defined in `src/agent/conversation_store.py:Ticket`.

| Field | Type | Notes |
|-------|------|-------|
| `id` | `str` | `TKT-{hex8}` — the public MCP ticket handle |
| `conversation_id` | `str` | UUID linking to parent Conversation |
| `status` | `TicketStatus` | `open → pending → resolved` or `open/pending → escalated` |
| `topics` | `list[str]` | Inferred topic tags |
| `opened_at` | `str` | UTC ISO-8601 timestamp |
| `closed_at` | `str \| None` | Set on RESOLVED or ESCALATED transition |

Valid transitions (enforced by `Ticket.transition()`):
```
OPEN → PENDING, ESCALATED
PENDING → RESOLVED, ESCALATED
RESOLVED → (none — terminal)
ESCALATED → (none — terminal)
```

### Conversation
Defined in `src/agent/conversation_store.py:Conversation`.

| Field | Type | Notes |
|-------|------|-------|
| `id` | `str` | UUID — internal handle |
| `customer_email` | `str` | Customer identity key |
| `channel_origin` | `str` | `email` / `whatsapp` / `web_form` |
| `messages` | `list[Message]` | Capped at MESSAGE_CAP=20 |
| `ticket` | `Ticket` | Embedded ticket (1-per-conversation) |
| `created_at` | `str` | UTC ISO-8601 |
| `updated_at` | `str` | UTC ISO-8601, updated on add_message |

### CustomerProfile
Defined in `src/agent/conversation_store.py:CustomerProfile`.

| Field | Type | Notes |
|-------|------|-------|
| `email` | `str` | Primary identity key |
| `name` | `str` | From first create_ticket call |
| `known_phones` | `set[str]` | Linked phone identifiers |
| `channels_used` | `set[str]` | All channels this customer has used |
| `topic_history` | `dict[str, list[str]]` | topic → [conversation_ids] |
| `conversation_ids` | `list[str]` | Ordered list of all conversation UUIDs |
| `created_at` | `str` | UTC ISO-8601 |

### Message
Defined in `src/agent/conversation_store.py:Message`.

| Field | Type | Notes |
|-------|------|-------|
| `id` | `str` | `msg-{hex8}` |
| `text` | `str` | Message content |
| `channel` | `str` | Channel at send time |
| `direction` | `"inbound" \| "outbound"` | |
| `timestamp` | `str` | UTC ISO-8601 |
| `sentiment_score` | `float \| None` | 0.0–1.0 (None for outbound) |

---

## New Adapter Structure (server.py only)

### `_ticket_index: dict[str, str]`

```
ticket_id (str)  →  conversation_id (str)
"TKT-a1b2c3d4"  →  "550e8400-e29b-41d4-a716-446655440000"
```

- **Scope**: Module-level variable in `src/mcp_server/server.py`
- **Populated**: On every `create_ticket` call
- **Used by**: `escalate_to_human`, `send_response`, `resolve_ticket`
- **Lifetime**: Co-terminous with the server process (in-memory only)
- **Rationale**: Bridges MCP public API (`ticket_id`) with store's internal addressing
  (`conversation_id`) without modifying Phase 2C code.

---

## MCP Tool Response Shapes

All tools return `str` (JSON-serialised). Shapes below show the Python dict before
`json.dumps()`.

### `search_knowledge_base` → success
```json
{
  "results": [
    {"section_title": "str", "content": "str", "relevance_score": 0.42}
  ],
  "count": 3,
  "query": "original query"
}
```

### `create_ticket` → success
```json
{
  "ticket_id": "TKT-a1b2c3d4",
  "customer_id": "user@example.com",
  "status": "open",
  "channel": "email",
  "created_at": "2026-04-02T10:00:00+00:00"
}
```

### `get_customer_history` → success
```json
{
  "customer_id": "user@example.com",
  "name": "Alice",
  "channels_used": ["email", "whatsapp"],
  "conversation_count": 2,
  "conversations": [
    {
      "conversation_id": "uuid",
      "channel": "email",
      "ticket_id": "TKT-a1b2c3d4",
      "ticket_status": "resolved",
      "message_count": 4,
      "created_at": "2026-04-01T08:00:00+00:00"
    }
  ]
}
```

### `escalate_to_human` → success
```json
{
  "escalation_id": "ESC-{hex8}",
  "ticket_id": "TKT-a1b2c3d4",
  "status": "escalated",
  "reason": "customer requested human",
  "escalated_at": "2026-04-02T10:05:00+00:00"
}
```

### `send_response` → success
```json
{
  "delivery_status": "delivered",
  "ticket_id": "TKT-a1b2c3d4",
  "channel": "email",
  "message_length": 120,
  "timestamp": "2026-04-02T10:06:00+00:00"
}
```

### `get_sentiment_trend` → success
```json
{
  "customer_id": "user@example.com",
  "trend": "deteriorating",
  "window_scores": [0.7, 0.4, 0.2],
  "window_size": 3,
  "recommend_escalation": true
}
```

### `resolve_ticket` → success
```json
{
  "ticket_id": "TKT-a1b2c3d4",
  "status": "resolved",
  "resolution_summary": "Issue resolved by resetting integration token.",
  "resolved_at": "2026-04-02T10:10:00+00:00"
}
```

### Error shape (all tools)
```json
{"error": "validation: channel must be one of: email, whatsapp, web_form", "tool": "create_ticket"}
```

---

## State Transition Diagram (ticket lifecycle via MCP tools)

```
[create_ticket] → OPEN
                    ↓
           [send_response]
                    ↓
                 PENDING ──────────────────────────→ ESCALATED
                    ↓                          [escalate_to_human]
           [resolve_ticket]
                    ↓
                RESOLVED
```

Notes:
- OPEN → ESCALATED is also valid (escalation can happen before any response is sent)
- RESOLVED and ESCALATED are terminal states; re-calling returns idempotent result or error
