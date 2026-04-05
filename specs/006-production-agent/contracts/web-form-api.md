# API Contracts: Phase 4C-iii — Web Support Form

**Branch**: `006-production-agent` | **Date**: 2026-04-05

---

## FastAPI Endpoints (Python Backend)

### POST /support/submit

Accepts a web form submission, persists the ticket, publishes to Kafka, returns display ID.

**Request** (`application/json`):
```json
{
  "name": "John Smith",
  "email": "john@example.com",
  "subject": "Billing problem with my account",
  "category": "billing",
  "priority": "high",
  "message": "I was charged twice for the Growth plan this month..."
}
```

**Pydantic input model** (`WebFormInput`):
```python
class WebFormInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    subject: str = Field(min_length=5, max_length=200)
    category: Literal["billing", "technical", "account", "general"]
    priority: Literal["low", "medium", "high", "urgent"]
    message: str = Field(min_length=20, max_length=2000)
```

**Response 201** (`application/json`):
```json
{
  "ticket_id": "TKT-A3F2C1B0",
  "internal_id": "a3f2c1b0-...",
  "status": "open",
  "created_at": "2026-04-05T10:30:00+05:00"
}
```

**Response 422** (Pydantic validation failure — FastAPI auto-generated):
```json
{
  "detail": [
    { "type": "string_too_short", "loc": ["body", "message"], "msg": "...", "input": "..." }
  ]
}
```

**Processing steps**:
1. `get_or_create_customer(pool, email=body.email, name=body.name)`
2. `create_conversation(pool, customer_id, channel="web_form")`
3. `add_message(pool, conversation_id, role="customer", content=body.message, channel="web_form")`
4. `create_ticket(pool, conversation_id, customer_id, channel="web_form", subject=body.subject, category=body.category, priority=body.priority)`
5. Publish `TicketMessage` to Kafka topic `fte.tickets.incoming`
6. Return `{ ticket_id, internal_id, status, created_at }`

**Error behaviour**: Returns HTTP 500 with `{ "detail": "Internal server error" }` on
any unhandled exception. Never returns 5xx from Kafka failures — log and continue.

---

### GET /support/ticket/{ticket_id}

Looks up a ticket by its display ID (TKT-XXXXXXXX format) or internal UUID.

**Path parameter**: `ticket_id` — either `TKT-A3F2C1B0` or full UUID string.

**Response 200** (`application/json`):
```json
{
  "ticket_id": "TKT-A3F2C1B0",
  "internal_id": "a3f2c1b0-...",
  "status": "in_progress",
  "category": "billing",
  "priority": "high",
  "subject": "Billing problem with my account",
  "message": "I was charged twice for the Growth plan this month...",
  "customer_name": "John Smith",
  "customer_email": "john@example.com",
  "created_at": "2026-04-05T10:30:00+05:00",
  "updated_at": "2026-04-05T10:35:00+05:00",
  "resolved_at": null
}
```

**Response 404** (`application/json`):
```json
{ "detail": "Ticket not found" }
```

**Lookup logic**:
- If `ticket_id` starts with `TKT-`: query `WHERE upper(substring(id::text, 1, 8)) = $1`
  (where `$1` is the 8-char suffix after `TKT-`).
- If `ticket_id` is a UUID: query `WHERE id = $1`.
- JOIN with `customers` table to get `customer_name` and `customer_email`.
- JOIN with `messages` to get original customer message (role='customer', first message).

---

### GET /metrics/summary

Returns aggregated support metrics and recent tickets for the dashboard.

**Response 200** (`application/json`):
```json
{
  "total": 143,
  "open": 12,
  "in_progress": 18,
  "resolved": 108,
  "escalated": 5,
  "escalation_rate": 3.5,
  "by_channel": {
    "email": 82,
    "whatsapp": 39,
    "web_form": 22
  },
  "recent_tickets": [
    {
      "ticket_id": "TKT-A3F2C1B0",
      "customer_name": "John Smith",
      "channel": "email",
      "category": "billing",
      "priority": "high",
      "status": "open",
      "created_at": "2026-04-05T10:30:00+05:00"
    }
  ]
}
```

**Query logic**:
```sql
-- Total and by-status counts
SELECT
  COUNT(*) AS total,
  COUNT(*) FILTER (WHERE status = 'open') AS open,
  COUNT(*) FILTER (WHERE status = 'in_progress') AS in_progress,
  COUNT(*) FILTER (WHERE status = 'resolved') AS resolved,
  COUNT(*) FILTER (WHERE status = 'escalated') AS escalated
FROM tickets;

-- Channel breakdown
SELECT channel, COUNT(*) AS cnt FROM tickets GROUP BY channel;

-- Recent 10 tickets (with customer join)
SELECT
  t.id, t.channel, t.category, t.priority, t.status, t.created_at,
  c.name AS customer_name
FROM tickets t
JOIN customers c ON c.id = t.customer_id
ORDER BY t.created_at DESC
LIMIT 10;
```

`escalation_rate` = `(escalated / total) * 100` rounded to 1 decimal.

---

## Next.js API Route Handlers (Proxies)

### POST /api/tickets → FastAPI POST /support/submit

```
app/api/tickets/route.ts
```

**Request**: Same body as FastAPI `WebFormInput`.  
**Response**: Pass-through (status + body) from FastAPI.

Transforms:
- Adds `Content-Type: application/json` header to upstream fetch.
- On network error (FastAPI unreachable): returns `{ error: "Service unavailable" }` with HTTP 503.

---

### GET /api/tickets/[id] → FastAPI GET /support/ticket/{id}

```
app/api/tickets/[id]/route.ts
```

**Request**: URL param `id` (from `[id]` dynamic segment).  
**Response**: Pass-through. 404 from FastAPI → 404 to client → `not-found.tsx` renders.

---

### GET /api/metrics → FastAPI GET /metrics/summary

```
app/api/metrics/route.ts
```

**Request**: No parameters.  
**Response**: Pass-through.

Cache headers: `Cache-Control: no-store` (always fresh, dashboard auto-refreshes).

---

## Environment Variables

| Variable | Where Used | Example |
|----------|-----------|---------|
| `FASTAPI_URL` | Next.js API routes (server-side only) | `http://localhost:8000` |
| `NEXT_PUBLIC_API_URL` | Placeholder — not used client-side | `http://localhost:8000` |
| `DATABASE_URL` | FastAPI → asyncpg | `postgresql://...` |
| `KAFKA_BOOTSTRAP_SERVERS` | FastAPI → aiokafka | `localhost:9092` |

**Note**: `FASTAPI_URL` is server-side only (used in API route handlers, never `NEXT_PUBLIC_`).
Client code hits `/api/tickets` (same-origin), never `http://localhost:8000` directly.
