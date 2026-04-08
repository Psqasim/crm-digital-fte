# API Reference

FastAPI backend for CRM Digital FTE Factory.

**Base URL (local):** `http://localhost:8000`  
**Interactive docs:** `http://localhost:8000/docs`

---

## Endpoints

### GET /health

Health check — returns service status and DB connectivity.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "connected",
  "timestamp": "Tuesday, April 08, 2026 at 03:45 PM PKT"
}
```

```bash
curl http://localhost:8000/health
```

---

### POST /support/submit

Submit a support ticket via web form.

**Request body:**
```json
{
  "name": "Jane Smith",
  "email": "jane@acme.com",
  "subject": "How do I set up automation rules?",
  "category": "general",
  "priority": "medium",
  "message": "I need help setting up my first automation rule in NexaFlow."
}
```

| Field | Type | Values |
|-------|------|--------|
| `name` | string | 1–200 chars |
| `email` | string | valid email |
| `subject` | string | 5–200 chars |
| `category` | enum | `billing`, `technical`, `account`, `general` |
| `priority` | enum | `low`, `medium`, `high`, `urgent` |
| `message` | string | 20–2000 chars |

**Response (201):**
```json
{
  "ticket_id": "TKT-A1B2C3D4",
  "customer_id": "uuid",
  "conversation_id": "uuid",
  "status": "open"
}
```

```bash
curl -X POST http://localhost:8000/support/submit \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Jane Smith",
    "email": "jane@acme.com",
    "subject": "How do I set up automation rules?",
    "category": "general",
    "priority": "medium",
    "message": "I need help setting up my first automation rule in NexaFlow."
  }'
```

---

### GET /support/ticket/{ticket_id}

Look up a ticket by display ID (`TKT-XXXXXXXX`) or UUID.

**Response (200):**
```json
{
  "ticket_id": "TKT-A1B2C3D4",
  "customer_name": "Jane Smith",
  "customer_email": "jane@acme.com",
  "subject": "How do I set up automation rules?",
  "status": "resolved",
  "channel": "web_form",
  "priority": "medium",
  "created_at": "2026-04-08T15:30:00+05:00"
}
```

```bash
curl http://localhost:8000/support/ticket/TKT-A1B2C3D4
```

---

### POST /agent/process/{ticket_id}

Run the AI agent on a specific ticket.

**Response (200):**
```json
{
  "ticket_id": "TKT-A1B2C3D4",
  "response_text": "To set up automation rules in NexaFlow, go to Settings → Automation...",
  "channel": "web_form",
  "escalated": false,
  "escalation_id": null,
  "resolution_status": "resolved",
  "error": null
}
```

```bash
curl -X POST http://localhost:8000/agent/process/TKT-A1B2C3D4
```

---

### POST /agent/process-pending

Enqueue all open/pending tickets for background processing.

**Response (200):**
```json
{
  "queued": 3,
  "ticket_ids": ["TKT-A1B2C3D4", "TKT-E5F6G7H8", "TKT-I9J0K1L2"]
}
```

```bash
curl -X POST http://localhost:8000/agent/process-pending
```

---

### GET /metrics/summary

Aggregated ticket metrics for the support dashboard.

**Response (200):**
```json
{
  "total_tickets": 42,
  "resolved": 31,
  "escalated": 8,
  "open": 3,
  "resolution_rate": 0.74,
  "recent_tickets": [...]
}
```

```bash
curl http://localhost:8000/metrics/summary
```

---

### GET /metrics/channels

Per-channel ticket breakdown.

**Response (200):**
```json
{
  "web_form": 20,
  "email": 15,
  "whatsapp": 7
}
```

```bash
curl http://localhost:8000/metrics/channels
```

---

### POST /webhooks/whatsapp

Twilio webhook receiver for inbound WhatsApp messages. Called by Twilio — not for direct use.

**Request:** `application/x-www-form-urlencoded` (Twilio format)  
**Response:** TwiML XML

---

### POST /webhooks/gmail

Gmail push notification receiver. Called by Google — not for direct use.

**Request:** JSON with Gmail notification payload  
**Response:** `{"status": "ok"}`
