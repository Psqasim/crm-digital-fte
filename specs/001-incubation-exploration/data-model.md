# Data Model: Phase 2B — Prototype Core Loop

**Date**: 2026-04-01
**Feature**: 001-incubation-exploration
**File**: `src/agent/models.py`

---

## Entity Overview

```
TicketMessage (input)
      │
      ▼
normalize_message()
      │
      ▼
NormalizedTicket
      │
      ├──► knowledge_base.search() ──► KBResult[]
      │
      ├──► escalation_evaluator.evaluate() ──► EscalationDecision
      │
      └──► agent.generate_response() ──► str (raw)
                                              │
                                              ▼
                               channel_formatter.format() ──► str (formatted)
                                              │
                                              ▼
                                        AgentResponse (output)
```

---

## Channel

```python
class Channel(str, Enum):
    EMAIL     = "email"
    WHATSAPP  = "whatsapp"
    WEB_FORM  = "web_form"
```

**Constraints**: Value MUST be one of the three literals. Any other value raises ValueError.
**Channel metadata** (preserved in NormalizedTicket):

| Channel | Primary Identifier | Subject Available | Pre-categorized |
|---------|-------------------|-------------------|-----------------|
| email | customer_email | Yes (subject field) | No |
| whatsapp | customer_phone | No (inferred from message) | No |
| web_form | customer_email | Yes (subject field) | Yes (category dropdown) |

---

## TicketMessage

The raw inbound message as received from any channel source.

```python
@dataclass
class TicketMessage:
    id: str                          # e.g., "TKT-001" or UUID
    channel: Channel                 # source channel
    customer_name: str               # display name
    customer_email: str | None       # None only for phone-only WhatsApp contacts
    customer_phone: str | None       # E.164 format, e.g., "+923001234567"
    subject: str | None              # None for WhatsApp (no subject field)
    message: str                     # raw message body
    received_at: str                 # ISO-8601 UTC timestamp
    metadata: dict                   # channel-specific extras (thread_id, wa_id, etc.)
    category: str | None             # pre-filled by web form; None for email/whatsapp
```

**Validation rules**:
- `customer_email` OR `customer_phone` MUST be non-null (at least one identifier required)
- `message` MUST be non-empty string (gibberish is allowed; emptiness is not)
- `channel` MUST be a valid `Channel` enum value

**Identity hierarchy**:
1. `customer_email` (primary key — used for cross-channel unification)
2. `customer_phone` (secondary — used when email not yet known, e.g., first WhatsApp contact)

---

## NormalizedTicket

Channel-agnostic internal representation. Created by `normalize_message()`.

```python
@dataclass
class NormalizedTicket:
    ticket_id: str                   # same as TicketMessage.id or newly generated
    channel: Channel                 # preserved from source
    customer_name: str               # first name extracted: "Sarah Mitchell" → "Sarah"
    customer_first_name: str         # extracted for greeting use
    customer_email: str | None       # from source
    customer_phone: str | None       # from source
    identifier_type: str             # "email" | "phone" | "both"
    inferred_topic: str              # subject for email/web; first-10-words for whatsapp
    message: str                     # original message body (never truncated here)
    message_word_count: int          # precomputed
    category_hint: str | None        # from web form pre-fill; None for other channels
    received_at: str                 # ISO-8601 UTC from source
    source_metadata: dict            # original metadata, never modified
    language_hint: str               # "en" default; "ur" / "es" etc. when detected
```

**Normalization rules by channel**:
- `email`: `inferred_topic = subject`; `identifier_type = "email"`
- `whatsapp`: `inferred_topic = " ".join(message.split()[:10])`; `identifier_type`
  depends on which identifiers are present
- `web_form`: `inferred_topic = subject`; `category_hint = category` from form

**Language detection** (simple prototype rule):
- Non-ASCII character ratio > 15%: tag as non-English (`language_hint = "non_en"`)
- Starts with common Spanish words ("hola", "ayuda", "estoy"): `language_hint = "es"`
- Default: `language_hint = "en"`

---

## KBResult

A single result from the knowledge base search.

```python
@dataclass
class KBResult:
    section_title: str               # e.g., "3. Integrations"
    content: str                     # section body text (max 500 chars for prompt)
    relevance_score: float           # Jaccard similarity score, 0.0–1.0
```

**Constraints**:
- `relevance_score` MUST be in range [0.0, 1.0]
- `content` is truncated to 500 chars before being passed to LLM (token budget)
- Maximum 3 `KBResult` objects returned per search call

---

## EscalationDecision

Output of the LLM-intent escalation evaluator.

```python
@dataclass
class EscalationDecision:
    should_escalate: bool            # True = human required
    reason: str                      # Human-readable reason, e.g., "refund_request"
    urgency: str                     # "low" | "normal" | "high"
    raw_llm_response: str            # raw JSON string from LLM (for debugging)
```

**Urgency semantics**:
- `"high"`: security incident, data breach, Enterprise SLA breach risk
- `"normal"`: refund, legal, explicit human request, 3+ follow-ups, sentiment < 0.3
- `"low"`: pricing negotiation (can wait for business hours)

---

## AgentResponse

The complete output of `process_ticket()`.

```python
@dataclass
class AgentResponse:
    ticket_id: str                   # references NormalizedTicket.ticket_id
    channel: Channel                 # for routing the response
    raw_response: str                # LLM output before channel formatting
    formatted_response: str          # channel-formatted, ready to send
    escalation: EscalationDecision   # always set; check .should_escalate
    kb_results_used: list[KBResult]  # which docs were referenced
    processing_time_ms: float        # total time from receive to response
    model_used: str                  # e.g., "gpt-4o"
    prompt_datetime: str             # the PKT datetime injected into the prompt
```

**State transitions**:
```
message received
      │
      ▼
[NORMALIZED] — NormalizedTicket created
      │
      ├─[ESCALATED]→ formatted_response = escalation_acknowledgment_template
      │                escalation.should_escalate = True
      │
      └─[RESOLVED]→ formatted_response = LLM response + channel formatting
                     escalation.should_escalate = False
```

**Invariants**:
- `formatted_response` is NEVER null or empty
- `escalation` is NEVER null (always evaluated)
- `processing_time_ms` > 0

---

## Data Flow Example (TKT-025, WhatsApp)

```
Input TicketMessage:
  id="TKT-025", channel=whatsapp, customer_name="Marcus Thompson",
  customer_email="marcus.t@buildright.co.uk", customer_phone="+447911123456",
  subject=None, message="My due date reminders stopped sending to Slack. Was working fine yesterday."

After normalize_message():
  ticket_id="TKT-025", channel=whatsapp, customer_first_name="Marcus",
  identifier_type="both", inferred_topic="My due date reminders stopped sending to",
  message_word_count=12, category_hint=None, language_hint="en"

After search_knowledge_base("due date reminders Slack automation"):
  KBResult(section_title="3. Integrations", content="Slack...token expiry...", score=0.38)
  KBResult(section_title="2. Task Automation Rules", content="Triggers...Due date...", score=0.31)

After evaluate_escalation():
  EscalationDecision(should_escalate=False, reason="standard_bug_report", urgency="normal")

After generate_response() + format_response():
  formatted_response = "Hi Marcus! 👋 That usually means the Slack token expired
                        (happens every 90 days). Head to Settings > Integrations >
                        Slack > Reconnect. Let me know if that helps!"
  (len = 189 chars ✅ under 300 soft limit)

Final AgentResponse:
  ticket_id="TKT-025", channel=whatsapp, escalation.should_escalate=False,
  formatted_response=<above>, processing_time_ms≈2300
```
