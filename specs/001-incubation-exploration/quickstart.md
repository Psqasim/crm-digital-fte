# Quickstart: Phase 2B Prototype

**Run the prototype in 5 minutes.**

---

## Prerequisites

- Python 3.12
- An OpenAI API key with access to `gpt-4o` and `gpt-4o-mini`

---

## 1. Install dependencies

```bash
cd /home/ps_qasim/projects/crm-digital-fte
pip install -r requirements.txt
```

Verify:
```bash
python -c "import openai, dotenv; print('OK')"
```

---

## 2. Set your API key

```bash
cp .env.example .env
# Edit .env and set: OPENAI_API_KEY=sk-your-key-here
```

---

## 3. Run the prototype against test tickets

```bash
python src/agent/prototype.py
```

Expected output (5 test tickets):

```
=== TKT-002 (email) ===
Escalated: False
Response preview: Dear James, Thank you for reaching out...

=== TKT-006 (email) ===
Escalated: True  ← furious customer + explicit human request
Urgency: high

=== TKT-025 (whatsapp) ===
Escalated: False
Response length: 189 chars  ← under 300 soft limit

=== TKT-032 (whatsapp) ===
Escalated: False
Response preview: Hi! 👋 It looks like your message may have...

=== TKT-044 (web_form) ===
Escalated: True  ← GDPR / legal compliance
Urgency: normal
```

---

## 4. Process a single ticket manually

```python
from src.agent.prototype import process_ticket
from src.agent.models import TicketMessage, Channel

ticket = TicketMessage(
    id="TKT-TEST",
    channel=Channel.WHATSAPP,
    customer_name="Alice Chen",
    customer_email=None,
    customer_phone="+923001234567",
    subject=None,
    message="My automation stopped working after the update",
    received_at="2026-04-01T10:00:00Z",
    metadata={"wa_id": "923001234567"},
    category=None,
)

response = process_ticket(ticket)
print(response.formatted_response)
print(f"Escalated: {response.escalation.should_escalate}")
print(f"Time: {response.processing_time_ms:.0f}ms")
```

---

## 5. Run verification tests

```bash
python tests/test_prototype.py
```

All 5 tests should pass. Expected:
- TKT-002, TKT-025, TKT-032: `should_escalate=False`
- TKT-006, TKT-044: `should_escalate=True`
- TKT-025 formatted_response: ≤ 1600 chars

---

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key |

---

## Prototype Limitations (by design)

| Limitation | Production Replacement |
|------------|----------------------|
| In-memory state (no DB) | PostgreSQL `tickets` table |
| Text search (Jaccard) | pgvector semantic search |
| Direct `openai` SDK | OpenAI Agents SDK |
| No Kafka | `fte.tickets.incoming` topic |
| Single process | Kubernetes HPA workers |

These are intentional incubation simplifications per constitution §8.
