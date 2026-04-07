# Tool Contracts: Phase 4B — Production Agent

**Branch**: `006-production-agent` | **Date**: 2026-04-04
**Module**: `production/agent/tools.py`

All 7 `@function_tool` decorated functions. Inputs validated by Pydantic (ADR-0003).
All tools return JSON strings. All tools are `async def`. None raise — errors returned as JSON.

---

## T1: search_knowledge_base

**Input** (`SearchKBInput` BaseModel):
```
query: str        # max_length=500, min_length=1
limit: int = 5   # ge=1, le=20
```

**Flow**: `query` → embed (text-embedding-3-small) → `queries.search_knowledge_base(pool, embedding, limit)`

**Success output**:
```json
{"results": [{"title": "...", "content": "...", "category": "...", "similarity": 0.87}], "count": 3}
```

**Error output**: `{"error": "<message>", "tool": "search_knowledge_base"}`
**Empty case**: `{"results": [], "count": 0}` — not an error

---

## T2: create_ticket

**Input** (`CreateTicketInput` BaseModel):
```
customer_id: str
conversation_id: str
channel: str        # email | whatsapp | web_form
subject: str | None = None
category: str | None = None
```

**Flow**: `queries.create_ticket(pool, conversation_id, customer_id, channel, subject, category)`

**Success output**:
```json
{"ticket_id": "uuid", "customer_id": "uuid", "conversation_id": "uuid", "channel": "email", "status": "open", "created_at": "2026-04-04T10:00:00Z"}
```

**Error output**: `{"error": "<message>", "tool": "create_ticket"}`

---

## T3: get_customer_history

**Input** (Annotated primitives):
```
customer_id: str
limit: int = 20
```

**Flow**: `queries.get_customer_history(pool, customer_id, limit)`

**Success output**:
```json
{"conversations": [{"conversation_id": "...", "channel": "email", "status": "resolved", "messages": [...]}], "count": 2}
```

**Empty case**: `{"conversations": [], "count": 0}` — not an error

---

## T4: escalate_to_human

**Input** (`EscalateInput` BaseModel):
```
ticket_id: str
reason: str        # min_length=1
urgency: str = "medium"   # low | medium | high | critical
```

**Flow**: `queries.update_ticket_status(pool, ticket_id, status="escalated", reason=reason)`

**Success output**:
```json
{"escalation_id": "uuid", "ticket_id": "uuid", "status": "escalated", "reason": "sentiment breach", "urgency": "high", "escalated_at": "2026-04-04T10:05:00Z"}
```

**Idempotent**: Re-escalating returns existing record, status 200.
**Error output**: `{"error": "ticket not found", "tool": "escalate_to_human"}`

---

## T5: send_response

**Input** (`SendResponseInput` BaseModel):
```
ticket_id: str
message: str       # min_length=1
channel: str       # email | whatsapp | web_form
```

**Flow**: Apply formatter → log to console (stub) → return confirmation

**Success output**:
```json
{"delivery_status": "stub_delivered", "ticket_id": "uuid", "channel": "email", "message_length": 342, "timestamp": "2026-04-04T10:05:30Z"}
```

**Phase 4B**: stub delivery. Phase 4C wires Gmail API / Twilio / Next.js without changing this signature.
**Length enforcement**: messages exceeding channel limits are truncated before return.
**Error output**: `{"error": "<message>", "tool": "send_response"}`

---

## T6: get_sentiment_trend

**Input** (Annotated primitives):
```
customer_id: str
last_n: int = 5
```

**Flow**: `queries.get_sentiment_trend(pool, customer_id, last_n)`

**Success output**:
```json
{"scores": [0.6, 0.4, 0.2], "count": 3, "trend": "deteriorating", "recommend_escalation": true}
```

**Trend logic** (computed in tool, not DB):
- `improving`: last score > first score by ≥ 0.2
- `deteriorating`: last score < first score by ≥ 0.2  
- `stable`: otherwise
- `recommend_escalation`: true if average < 0.3

**Empty case**: `{"scores": [], "count": 0, "trend": "insufficient_data", "recommend_escalation": false}`

---

## T7: resolve_ticket

**Input** (`ResolveTicketInput` BaseModel):
```
ticket_id: str
resolution_summary: str   # min_length=1
```

**Flow**: `queries.update_ticket_status(pool, ticket_id, status="resolved", reason=resolution_summary)`

**Success output**:
```json
{"ticket_id": "uuid", "status": "resolved", "resolution_summary": "Walked customer through OAuth reconnect.", "resolved_at": "2026-04-04T10:10:00Z"}
```

**Idempotent**: Already-resolved ticket returns existing record without error.
**Error output**: `{"error": "cannot resolve escalated ticket", "tool": "resolve_ticket"}` for ESCALATED tickets.
