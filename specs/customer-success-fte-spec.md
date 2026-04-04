# Customer Success FTE Specification
## NexaFlow — CRM Digital FTE Factory

**Version:** 1.0.0
**Phase:** 2F — Crystallized Specification
**Branch:** `003-mcp-server`
**Date:** 2026-04-04
**Status:** Authoritative — Single Source of Truth for Production Build

> This document is the crystallized output of Incubation Phases 2A–2E. Every
> requirement, edge case, tool definition, and performance target below is derived
> from real ticket analysis, prototype execution, or explicit constitution rules —
> not from guesswork or generic template text. It supersedes any earlier draft or
> exploration note for purposes of production planning.

---

## 1. Purpose

Handle routine NexaFlow customer support queries with speed and consistency across
Email (Gmail), WhatsApp (Twilio), and Web Form channels — 24 hours a day, 365 days a
year — at an operating cost of less than $1,000/year.

**Business problem solved:** NexaFlow processes approximately 800 support tickets per
week across three heterogeneous channels. A human FTE costs $75,000/year and is only
available Monday–Friday, 9 AM–6 PM PKT. The Digital FTE resolves ≥75% of tickets
autonomously without human escalation, providing deterministic, brand-consistent
responses at near-zero marginal cost per additional ticket.

**What the agent does:**

1. Accepts incoming messages from Email, WhatsApp, and Web Form
2. Normalises each message into a unified ticket event regardless of source channel
3. Resolves customer identity across all channels using email as primary key
4. Searches the NexaFlow knowledge base for relevant product documentation
5. Generates a channel-appropriate, empathetic response
6. Decides whether to escalate to a human agent based on 8 defined triggers
7. Records every interaction with full channel metadata for audit and reporting

**What the agent does NOT do:** Replace human judgment on legal, financial, security,
or emotionally critical issues; serve as a full website (Web Support Form only); integrate
with external CRMs (PostgreSQL schema IS the CRM); operate a production WhatsApp Business
account (Twilio Sandbox for development).

---

## 2. Supported Channels

All three channels funnel into a single `fte.tickets.incoming` Kafka topic before agent
processing. No channel may bypass the queue (Constitution Rule III-1).

| Channel | Identifier | Response Style | Greeting | Max Length | Sign-off |
|---------|------------|----------------|----------|------------|---------|
| **Email (Gmail)** | Email address | Formal, detailed | "Dear [FirstName]," | 500 words | NexaFlow signature block |
| **WhatsApp (Twilio)** | Phone number (E.164) | Conversational, concise | "Hi [FirstName]! 👋" | 3 sentences / 1600 chars absolute | Natural ("Let me know!") |
| **Web Form** | Email address | Semi-formal + next steps | "Hi [FirstName]," | 300 words / 1000 chars | Support link |

**Channel-specific constraints (hard-coded into Channel Adaptation Skill):**

- **Email:** Full paragraphs with proper punctuation; NexaFlow signature appended on every
  reply; no strict emoji policy but professional tone enforced; subject line threading via
  Gmail API (Gmail Message-ID header).
- **WhatsApp:** Maximum 1 emoji per message; acceptable: ✅ 👋 😊; prohibited: 🔥 💯 🎉 🚀;
  no markdown headers or bullet lists; plain text only; 24-hour active conversation window
  for same-day multi-message threading (R14 from discovery).
- **Web Form:** Light markdown (bold for key steps) acceptable; brief bullet list
  acceptable for multi-step answers; no signature block; optional short greeting.

**Identity unification per channel (Constitution Rule III-2):**

- Email → email address is primary key
- WhatsApp → phone number (E.164) is secondary key, linked to email via `customer_identifiers`
  table; customers who never provide email get a phone-scoped anonymous profile until email
  is captured
- Web Form → email address is primary key (same as email channel)

---

## 3. Scope

### In Scope

The agent autonomously handles:

- Product feature questions (how does X work, what plan includes Y)
- How-to guidance (step-by-step integration setup, workflow configuration)
- Bug report intake (receive, classify, search KB for known fix, respond or log)
- Feedback and general inquiries
- Password reset and account access guidance
- Standard integration setup help (Slack, Jira, Zapier, HubSpot as documented in product docs)
- Plan feature comparisons (Starter vs Growth vs Enterprise — from published pricing page only)
- Cross-channel conversation continuity (acknowledges prior channel history on every interaction)
- Multi-message conversation threading within a 24-hour window (WhatsApp)
- Language detection and same-language response (English, Spanish, Urdu — see R4)

### Out of Scope (Escalate to Human)

The following categories MUST NOT be resolved by AI. The agent escalates immediately:

| Category | Escalation Trigger | Target Channel |
|----------|--------------------|----------------|
| Pricing negotiation | Discount request, custom pricing, competitor price match | Sales/CSM team |
| Refund request | Any explicit refund mention (intent-detected, not keyword) | #billing-escalations |
| Legal / compliance | GDPR, CCPA, data breach, lawsuit, subpoena, DPA | #support-escalations |
| Angry customer | Sentiment score < 0.3 (0.0–1.0 scale) | #support-escalations |
| Security incident | Unauthorized access, data theft, wrong data visible | #security-incidents (immediate) |
| Explicit human request | "speak to a human", "real agent", "manager" | Acknowledge + queue |
| 3+ unanswered follow-ups | Same customer, 3+ messages without resolution | #support-escalations |
| Enterprise SLA breach risk | Enterprise ticket open 3+ hours (SLA = 4 hrs) | On-call CSM (P1) |

**Non-escalation guidance:** Simple how-to questions, password resets, plan feature
inquiries, standard bug reports with known fixes, and integration setup help are NOT
escalated even if the customer's tone is frustrated — unless sentiment score drops below 0.3.

**Critical lesson from incubation (TKT-003, TKT-042, TKT-051):** Escalation triggers MUST
be LLM-intent-based, NOT keyword-based. The word "charged" appears in both refund requests
and innocent billing questions. The phrase "manager" appears as a job title. Keyword matching
produces false positives that waste human agent time. See R11 in discovery-log.md.

---

## 4. Agent Skills

Five skills are formally defined as behavioral contracts. They are invoked in mandatory order
on every incoming message. Skills delegate execution to existing `src/agent/` modules and
MCP tools — they do NOT reimplement business logic.

### Invocation Order (Mandatory)

```
[INBOUND MESSAGE]
       │
       ▼
1. Customer Identification   (priority 0 — always first; no other skill runs before this)
       │
       ▼
2. Sentiment Analysis        (priority 1 — every message; uses resolved customer_id)
       │
       ▼
3. Knowledge Retrieval       (priority 2 — only if product question detected)
       │
       ▼
4. [Response Generation]     (agent drafts reply using KB results)
       │
       ▼
5. Escalation Decision       (priority 3 — evaluate before sending; skip drafting if sentiment escalates)
       │
       ├──[should_escalate: true]──► Call escalate_to_human MCP tool
       │
       └──[should_escalate: false]─►
                                     │
                                     ▼
                            6. Channel Adaptation   (priority 4 — always before send)
                                     │
                                     ▼
                            7. [send_response MCP tool]
```

---

### Skill 1 — Customer Identification

| Field | Value |
|-------|-------|
| `skill_id` | `customer_identification_v1` |
| **Trigger** | FIRST step on every inbound message; no other skill may run until `customer_id` is resolved |
| **Priority** | 0 (highest) |

**Inputs:**

| Parameter | Type | Required | Notes |
|-----------|------|----------|-------|
| `channel` | `email \| whatsapp \| web_form` | Yes | Source channel |
| `email` | string (email format) | No | Present for email and web_form channels |
| `phone` | string (E.164) | No | Present for whatsapp channel |
| `display_name` | string | No | Name from message metadata |
| `raw_message_id` | string | Yes | Channel-specific ID for idempotency |

**Outputs:**

| Field | Type | Description |
|-------|------|-------------|
| `customer_id` | string | Stable unified identifier across all channels |
| `is_returning_customer` | boolean | True if prior record exists |
| `customer_plan` | `starter \| growth \| enterprise \| unknown` | For SLA routing |
| `merged_history_summary` | object | `total_tickets`, `open_tickets`, `last_channel`, `last_interaction_timestamp` |
| `resolution_action` | `matched_existing \| created_new \| matched_by_cross_channel_link` | How ID was resolved |

**Connected Tools:**
- `src/agent/conversation_store.py` → `ConversationStore.resolve_identity()`
- `src/agent/models.py` → `CustomerProfile`

**Guardrails:**
- MUST NOT proceed without resolving at least a temporary `customer_id` (even for anonymous sessions)
- MUST NOT merge two customer profiles without at least one shared identifier (email or phone)
- MUST NOT expose PII (raw email or phone) in output — output `customer_id` only
- MUST create a new profile (`is_returning_customer: false`) rather than failing when no match found
- MUST be idempotent — calling with the same `raw_message_id` twice returns the same `customer_id`

---

### Skill 2 — Sentiment Analysis

| Field | Value |
|-------|-------|
| `skill_id` | `sentiment_analysis_v1` |
| **Trigger** | EVERY incoming customer message, immediately after Customer Identification resolves `customer_id` |
| **Priority** | 1 |

**Inputs:**

| Parameter | Type | Required | Notes |
|-----------|------|----------|-------|
| `message_text` | string | Yes | Full text of incoming message |
| `customer_id` | string | Yes | Resolved customer identifier for trend history |
| `conversation_history` | array of `{role, text, timestamp}` | No | Prior messages (oldest first) |

**Outputs:**

| Field | Type | Description |
|-------|------|-------------|
| `sentiment_score` | float [-1.0, 1.0] | Negative = frustration; positive = satisfaction |
| `sentiment_label` | `positive \| neutral \| negative` | Categorical label |
| `trend_label` | `improving \| stable \| deteriorating \| insufficient_data` | Derived from last 3+ interactions |
| `escalation_recommended` | boolean | True when trend is deteriorating or score < -0.6 |
| `data_points_used` | integer | Number of prior messages used to compute trend |

**Connected Tools:**
- `src/mcp_server/server.py` → `get_sentiment_trend` MCP tool
- `src/agent/conversation_store.py` → `ConversationStore.compute_sentiment_trend()`
- `src/agent/escalation_evaluator.py` → `evaluate_escalation()`

**Guardrails:**
- MUST NOT skip invocation even if message appears clearly positive
- MUST NOT store sentiment scores under a different `customer_id` than the resolved one
- MUST NOT recommend escalation solely based on one message unless score < -0.8
- MUST return `trend_label: "insufficient_data"` (not an error) when fewer than 3 prior messages exist

---

### Skill 3 — Knowledge Retrieval

| Field | Value |
|-------|-------|
| `skill_id` | `knowledge_retrieval_v1` |
| **Trigger** | When customer message contains a question about NexaFlow features, pricing, integrations, plans, or usage; also when agent needs factual product content |
| **Priority** | 2 |

**Inputs:**

| Parameter | Type | Required | Notes |
|-----------|------|----------|-------|
| `query` | string (max 500 chars) | Yes | Customer's question or topic |

**Outputs:**

| Field | Type | Description |
|-------|------|-------------|
| `results` | array | Ordered list of matching documentation snippets |
| `results[].section_title` | string | Documentation section heading |
| `results[].snippet` | string (max 400 chars) | Relevant excerpt |
| `results[].relevance_score` | float [0.0, 1.0] | Jaccard similarity score (Phase 2B); pgvector cosine (Phase 4) |
| `result_count` | integer | Number of results returned |
| `query_echo` | string | Query as received (for logging) |

**Connected Tools:**
- `src/mcp_server/server.py` → `search_knowledge_base` MCP tool
- `src/agent/knowledge_base.py` → `KnowledgeBase.search()`

**Guardrails:**
- MUST NOT invent or synthesize content not present in the knowledge base
- MUST NOT return results from a previous query when current query returns empty
- MUST NOT expose raw file paths or internal module names in output
- MUST NOT block if result count is zero — return empty array, not an error

---

### Skill 4 — Escalation Decision

| Field | Value |
|-------|-------|
| `skill_id` | `escalation_decision_v1` |
| **Trigger** | AFTER agent drafts a response but BEFORE sending it; also immediately if Sentiment Analysis returns `escalation_recommended: true` |
| **Priority** | 3 |

**Inputs:**

| Parameter | Type | Required | Notes |
|-----------|------|----------|-------|
| `customer_id` | string | Yes | Resolved customer identifier |
| `ticket_id` | string | Yes | Created ticket reference |
| `customer_plan` | `starter \| growth \| enterprise` | Yes | For SLA-based escalation logic |
| `ticket_age_minutes` | integer | Yes | Minutes elapsed since `opened_at` |
| `sentiment_trend` | `improving \| stable \| deteriorating \| insufficient_data` | Yes | From Skill 2 output |
| `escalation_recommended_by_sentiment` | boolean | Yes | From Skill 2 output |
| `message_text` | string | Yes | Latest message — checked for explicit triggers |
| `previous_escalations` | integer | No (default: 0) | Prior escalations in last 30 days |

**Outputs:**

| Field | Type | Description |
|-------|------|-------------|
| `should_escalate` | boolean | Escalation decision |
| `reason` | string (nullable) | Human-readable explanation |
| `urgency` | `low \| medium \| high \| critical` (nullable) | Populated only when `should_escalate: true` |

**SLA thresholds (from `context/escalation-rules.md`):**

| Plan | SLA | Auto-escalate at |
|------|-----|-----------------|
| Enterprise | 4 hours | 3+ hours open (240 min) |
| Growth | 24 hours | — (no auto SLA escalation) |
| Starter | None | — (no SLA) |

**Connected Tools:**
- `src/mcp_server/server.py` → `escalate_to_human` MCP tool
- `src/agent/escalation_evaluator.py` → `evaluate_escalation()`
- `context/escalation-rules.md` — authoritative trigger definitions

**Guardrails:**
- MUST NOT escalate based solely on ticket age for Starter-tier customers (no SLA)
- MUST escalate (`should_escalate: true`, `urgency: critical`) when `message_text` contains explicit threats, profanity, or legal trigger phrases
- MUST NOT silently suppress escalation if `escalate_to_human` MCP tool is unavailable — surface error
- MUST NOT change ticket status itself — that is the responsibility of the `escalate_to_human` MCP tool

---

### Skill 5 — Channel Adaptation

| Field | Value |
|-------|-------|
| `skill_id` | `channel_adaptation_v1` |
| **Trigger** | EVERY outbound response, immediately before `send_response` MCP tool is called; no response may be dispatched without passing through this skill |
| **Priority** | 4 |

**Inputs:**

| Parameter | Type | Required | Notes |
|-----------|------|----------|-------|
| `response_text` | string | Yes | Raw response draft from agent |
| `target_channel` | `email \| whatsapp \| web_form` | Yes | Delivery channel |
| `customer_name` | string (nullable) | No | Used for personalized greeting |
| `agent_signature_enabled` | boolean (default: true) | No | Suppress signature when false |

**Outputs:**

| Field | Type | Description |
|-------|------|-------------|
| `formatted_response` | string | Response after channel-specific formatting |
| `channel_applied` | string | Echo of `target_channel` (for logging) |
| `formatting_notes` | array of string | Transformations applied (e.g., "truncated to 3 sentences", "added signature") |

**Channel formatting rules:**

| Channel | Greeting | Structure | Signature | Emoji |
|---------|----------|-----------|-----------|-------|
| `email` | "Dear [Name]," or "Hello [Name]," | Full paragraphs | ✅ NexaFlow block | Professional only |
| `whatsapp` | None | Max 3 sentences; plain text | ❌ | Max 1; from approved set |
| `web_form` | "Hi [Name]," (optional) | 2–6 sentences or short bullet list | ❌ | Optional, minimal |

**Connected Tools:**
- `src/agent/channel_formatter.py` → `format_email_response()`, `format_whatsapp_response()`, `format_web_form_response()`
- `src/mcp_server/server.py` → `send_response` MCP tool (called AFTER this skill, not by it)

**Guardrails:**
- MUST NOT send the unformatted `response_text` directly — always apply channel rules
- MUST NOT add a signature block to `whatsapp` or `web_form` channels
- MUST NOT exceed 3 sentences for `whatsapp` — truncate with "…" if necessary
- MUST NOT alter factual content during formatting — only structure and style may change
- MUST return the response unchanged (with a `formatting_notes` warning) for an unrecognised channel value, rather than raising an error

---

## 5. MCP Tools

Seven tools are exposed via FastMCP stdio server (`src/mcp_server/server.py`). All tools return
JSON strings. All tools validate inputs and return structured error JSON (never raise exceptions
to the caller).

### Tool 1 — `search_knowledge_base`

| Field | Value |
|-------|-------|
| **Purpose** | Search NexaFlow product documentation for relevant information |
| **Module** | `src/mcp_server/server.py` → `search_knowledge_base()` |
| **Backed by** | `src/agent/knowledge_base.py` → `KnowledgeBase.search()` |

**Input schema:**

| Parameter | Type | Required | Constraints |
|-----------|------|----------|-------------|
| `query` | string | Yes | Must not be empty or whitespace-only |

**Output (success):**
```json
{
  "results": [
    {"section_title": "...", "content": "...", "relevance_score": 0.75}
  ],
  "count": 1,
  "query": "original query text"
}
```

**Error behavior:** Returns `{"error": "validation: query must not be empty", "tool": "search_knowledge_base"}` for empty input. Returns `{"error": "<exception message>", "tool": "search_knowledge_base"}` for internal errors. Never raises.

---

### Tool 2 — `create_ticket`

| Field | Value |
|-------|-------|
| **Purpose** | Create a new support ticket for a customer; MUST be called before any response is generated |
| **Module** | `src/mcp_server/server.py` → `create_ticket()` |
| **Backed by** | `ConversationStore.get_or_create_customer()`, `get_or_create_conversation()` |

**Input schema:**

| Parameter | Type | Required | Constraints |
|-----------|------|----------|-------------|
| `customer_id` | string | Yes | Email address or `phone:+E164` for WhatsApp |
| `issue` | string | Yes | Description of the issue (stored as topic, truncated to 100 chars) |
| `priority` | string | Yes | One of: `low`, `medium`, `high`, `critical` |
| `channel` | string | Yes | One of: `email`, `whatsapp`, `web_form` |

**Output (success):**
```json
{
  "ticket_id": "TKT-a1b2c3d4",
  "customer_id": "user@example.com",
  "status": "open",
  "channel": "email",
  "created_at": "2026-04-04T10:00:00+00:00"
}
```

**Error behavior:** Returns validation error JSON for invalid `priority` or `channel` values; for empty `customer_id` or `issue`. Never raises.

---

### Tool 3 — `get_customer_history`

| Field | Value |
|-------|-------|
| **Purpose** | Retrieve full interaction history for a customer across ALL channels |
| **Module** | `src/mcp_server/server.py` → `get_customer_history()` |
| **Backed by** | `ConversationStore.get_customer()`, `store._conversations` |

**Input schema:**

| Parameter | Type | Required |
|-----------|------|----------|
| `customer_id` | string | Yes |

**Output (success):**
```json
{
  "customer_id": "user@example.com",
  "name": "James Okonkwo",
  "channels_used": ["email", "web_form"],
  "conversation_count": 2,
  "conversations": [
    {
      "conversation_id": "conv-xyz",
      "channel": "email",
      "ticket_id": "TKT-001",
      "ticket_status": "resolved",
      "message_count": 3,
      "created_at": "2026-04-01T08:00:00+00:00"
    }
  ]
}
```

**Error behavior:** Returns `{"customer_id": "...", "conversation_count": 0, "conversations": []}` for unknown customers (not an error — customer not found is a valid state). Never raises.

---

### Tool 4 — `escalate_to_human`

| Field | Value |
|-------|-------|
| **Purpose** | Escalate a support ticket to a human agent; transitions ticket status to ESCALATED |
| **Module** | `src/mcp_server/server.py` → `escalate_to_human()` |
| **Backed by** | `ConversationStore.transition_ticket()` |

**Input schema:**

| Parameter | Type | Required |
|-----------|------|----------|
| `ticket_id` | string | Yes |
| `reason` | string | Yes |

**Output (success):**
```json
{
  "escalation_id": "ESC-a1b2c3d4",
  "ticket_id": "TKT-a1b2c3d4",
  "status": "escalated",
  "reason": "customer requested human agent",
  "escalated_at": "2026-04-04T10:05:00+00:00"
}
```

**Error behavior:** Returns `{"error": "ticket TKT-xxx not found"}` for unknown ticket IDs. Returns validation error JSON for empty inputs. ESCALATED is a terminal state — cannot re-escalate. Never raises.

---

### Tool 5 — `send_response`

| Field | Value |
|-------|-------|
| **Purpose** | Send a formatted response to the customer through the specified channel (simulated in Phase 2D; real dispatch in Phase 4) |
| **Module** | `src/mcp_server/server.py` → `send_response()` |
| **Backed by** | `ConversationStore.add_message()` |

**Input schema:**

| Parameter | Type | Required | Constraints |
|-----------|------|----------|-------------|
| `ticket_id` | string | Yes | Must exist in ticket index |
| `message` | string | Yes | Channel-adapted response text |
| `channel` | string | Yes | One of: `email`, `whatsapp`, `web_form` |

**Output (success):**
```json
{
  "delivery_status": "delivered",
  "ticket_id": "TKT-a1b2c3d4",
  "channel": "email",
  "message_length": 342,
  "timestamp": "2026-04-04T10:05:30+00:00"
}
```

**Error behavior:** Returns `{"error": "ticket TKT-xxx not found"}` for unknown tickets. Returns validation error JSON for invalid `channel` or empty `message`. Delivery is logged to stderr only — never stdout (preserves JSON-RPC protocol). Never raises.

---

### Tool 6 — `get_sentiment_trend`

| Field | Value |
|-------|-------|
| **Purpose** | Analyse sentiment trend for a customer based on recent message history |
| **Module** | `src/mcp_server/server.py` → `get_sentiment_trend()` |
| **Backed by** | `ConversationStore.compute_sentiment_trend()` |

**Input schema:**

| Parameter | Type | Required |
|-----------|------|----------|
| `customer_id` | string | Yes |

**Output (success):**
```json
{
  "customer_id": "user@example.com",
  "trend": "stable",
  "window_scores": [0.6, 0.5, 0.7],
  "window_size": 3,
  "recommend_escalation": false
}
```

**Error behavior:** Returns `{"trend": "stable", "window_scores": [], "recommend_escalation": false, "note": "no history found"}` for unknown customers. Returns `"note": "insufficient data"` when fewer than 2 messages exist. Never raises.

---

### Tool 7 — `resolve_ticket`

| Field | Value |
|-------|-------|
| **Purpose** | Mark a support ticket as resolved with a resolution summary |
| **Module** | `src/mcp_server/server.py` → `resolve_ticket()` |
| **Backed by** | `ConversationStore.transition_ticket()` (OPEN→PENDING→RESOLVED auto-cascade) |

**Input schema:**

| Parameter | Type | Required |
|-----------|------|----------|
| `ticket_id` | string | Yes |
| `resolution_summary` | string | Yes |

**Output (success):**
```json
{
  "ticket_id": "TKT-a1b2c3d4",
  "status": "resolved",
  "resolution_summary": "Walked customer through Slack OAuth reconnect steps.",
  "resolved_at": "2026-04-04T10:10:00+00:00"
}
```

**Error behavior:** Idempotent — if ticket is already RESOLVED, returns existing resolution without state change. Cannot resolve an ESCALATED ticket directly (returns error). Never raises.

---

## 6. Conversation State Model

All state is held in-memory by `ConversationStore` (Phase 2C). Phase 4 migrates to Neon
PostgreSQL with the same logical model. The in-memory implementation is in
`src/agent/conversation_store.py`.

### Key Entities

**CustomerProfile** — one record per customer, unified across all channels

| Field | Type | Description |
|-------|------|-------------|
| `email` | string | Primary key — email address |
| `name` | string | Display name from first contact |
| `channels_used` | `set[str]` | All channels this customer has used |
| `conversation_ids` | `list[str]` | All conversation IDs for this customer |
| `phone` | string (optional) | E.164 phone number (WhatsApp identifier) |

---

**Conversation** — one record per support interaction session

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | UUID-based conversation ID |
| `customer_email` | string | FK → CustomerProfile |
| `channel_origin` | string | Channel where conversation started |
| `messages` | `list[Message]` | Ordered message history (capped at 20) |
| `ticket` | `Ticket` | Associated ticket record |
| `created_at` | string | ISO-8601 UTC timestamp |

---

**Message** — one record per inbound or outbound message

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Message ID |
| `text` | string | Message content |
| `channel` | string | Channel of this specific message |
| `direction` | `"inbound" \| "outbound"` | Customer → Agent or Agent → Customer |
| `timestamp` | string | ISO-8601 UTC timestamp |
| `sentiment_score` | float (nullable) | Score recorded at message processing time |

---

**Ticket** — lifecycle tracker for a support request

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | `TKT-<8 hex chars>` |
| `conversation_id` | string | FK → Conversation |
| `status` | `TicketStatus` | Current status (see state machine below) |
| `topics` | `list[str]` | Topics discussed (max 100 chars each) |
| `opened_at` | string | ISO-8601 UTC — SLA clock starts here |
| `closed_at` | string (nullable) | ISO-8601 UTC — populated on RESOLVED |

---

**SentimentTrend** — computed on-demand from last 3 messages

| Field | Type | Description |
|-------|------|-------------|
| `label` | `SentimentLabel` | `improving \| stable \| deteriorating` |
| `window_scores` | `list[float]` | Scores of last N messages |
| `window_size` | integer (default: 3) | Number of messages in trend window |

---

### Ticket State Machine

```
        create_ticket()
              │
              ▼
           OPEN
           │   │
           │   └──[3+ hrs, Enterprise]──► (auto-escalation trigger)
           │
           ▼
        PENDING        (send_response called; waiting for customer reply or resolution)
           │   │
           │   └──[escalate_to_human]──►  ESCALATED  ─── (terminal)
           │
           └──[resolve_ticket]──►         RESOLVED   ─── (terminal)
```

**Valid transitions:**
- `OPEN` → `PENDING` (response sent)
- `OPEN` → `ESCALATED` (immediate escalation before response)
- `PENDING` → `RESOLVED` (ticket closed)
- `PENDING` → `ESCALATED` (escalation after initial response)
- `RESOLVED` → (none — terminal)
- `ESCALATED` → (none — terminal)

**Auto-cascade:** `resolve_ticket` MCP tool automatically transitions `OPEN → PENDING → RESOLVED` if the agent skips the PENDING step.

---

### Cross-Channel Identity Resolution

Primary lookup flow:

1. Extract identifiers from incoming message: `email`, `phone`, or both
2. Look up `email` in `CustomerProfile` store → if found, return existing `customer_id`
3. If no email match, look up `phone` in cross-channel link table → resolve to linked email → return `customer_id`
4. If no match on either identifier → create new `CustomerProfile` with available identifiers
5. Record `resolution_action`: `matched_existing` / `created_new` / `matched_by_cross_channel_link`

**Canonical cross-channel cases confirmed during incubation:**

- **James Okonkwo** (`james@techvault.io`): Email (TKT-002) → Web Form (TKT-052, explicitly references TKT-002). Same email key — automatically linked.
- **Marcus Thompson** (`marcus.t@buildright.co.uk`): WhatsApp (TKT-025) → Web Form (TKT-050, says "I reached out via WhatsApp earlier"). Email present in both records — automatically linked. Without cross-channel lookup, agent would repeat the same failed fix.

---

## 7. Performance Requirements

All targets are sourced from `constitution.md` §3 (Definition of Done) and the hackathon rubric. No guesses.

| Metric | Target | Source |
|--------|--------|--------|
| P95 processing latency | < 3 seconds (all channels) | Constitution §3 |
| First response time (end-to-end) | < 2 minutes from ticket submission | Company profile |
| AI resolution rate | > 75% (escalation rate < 25%) | Constitution §3 |
| Cross-channel identification accuracy | > 95% | Hackathon rubric |
| Response accuracy on test set | > 85% | Hackathon rubric |
| Escalation rate (sample baseline) | 9/60 = 15% — within target | discovery-log.md |
| Negative sentiment rate (sample) | 10/60 = 16.7% | discovery-log.md |
| Operating cost | < $1,000/year | Constitution §II |

**Volume targets for production readiness (24-hour continuous operation test):**

| Channel | Minimum volume |
|---------|----------------|
| Web Form | 100+ submissions processed end-to-end |
| Gmail | 50+ emails received, processed, replied |
| WhatsApp | 50+ messages received, processed, replied |
| Cross-channel | 10+ customers identified across 2+ channels |

**Reliability targets:**

- Uptime > 99.9% (≤ 1.4 minutes downtime in 24 hours)
- Survives random pod kills every 2 hours (chaos testing via `kubectl delete pod`)
- Zero message loss (every Kafka event reaches agent or dead-letter queue)

**Alert thresholds (from constitution):**

- Escalation rate > 25% → alert
- P95 latency > 3s → alert

---

## 8. Guardrails (Non-Negotiable)

These rules are hard-coded into the agent system prompt. Violation of any rule is a defect, not
a configuration choice. All ALWAYS/NEVER rules below are from `constitution.md` §IV.

### ALWAYS — Required behaviors

1. **Inject current datetime:**
   ```python
   from datetime import datetime
   from zoneinfo import ZoneInfo

   current_dt = datetime.now(ZoneInfo("Asia/Karachi"))
   system_prompt = f"""
   You are NexaFlow's AI support agent.
   Current date and time: {current_dt.strftime("%A, %B %d, %Y at %I:%M %p PKT")}
   ...
   """
   ```
   Required for: SLA breach detection, correct timestamp references, scheduling context. The agent MUST NEVER guess or infer the current date from training data.

2. **Create ticket before responding:** Call `create_ticket` BEFORE generating any customer response. Enforced tool call order:
   `create_ticket` → `get_customer_history` → `search_knowledge_base` (if needed) → `send_response`

3. **Check full cross-channel history:** Call `get_customer_history` on every interaction. If a customer has contacted before on any channel, acknowledge it in the response.

4. **Analyze sentiment before closing:** Every ticket close MUST have a sentiment score recorded. Tickets with sentiment < 0.3 MUST escalate before closure.

5. **Use customer's first name** at least once per response.

6. **Acknowledge frustration before solutions:** If the customer is clearly upset, the first sentence MUST validate their experience before offering help.

7. **End with a help offer:** Every response ends with an offer to assist further.

### NEVER — Prohibited behaviors

1. **Discuss competitor products** by name or implication: Asana, Monday.com, ClickUp, Notion, Trello, Basecamp, Linear, Jira (as project tool), Airtable, Smartsheet.

2. **Promise unreleased features.** Standard response: "I'm not able to share details about upcoming features, but I'd love to pass your feedback to our product team."

3. **Reveal internal pricing strategies**, discount thresholds, or negotiation flexibility.

4. **Guess the current date from training data.** Always use the injected PKT datetime.

5. **Respond to a customer without calling `send_response` tool.**

6. **Exceed channel limits:** Email ≤ 500 words, WhatsApp ≤ 1600 chars (3 sentences preferred), Web Form ≤ 1000 chars / 300 words.

7. **Say "I don't know"** — say "Let me look into that for you" or "Great question — here's what I can tell you" instead.

8. **Reveal internal system details**, tool names, or processing architecture to customers.

---

## 9. Edge Cases & Handling

All edge cases below were discovered during Phase 2A ticket analysis. Ticket IDs reference
`tests/edge_cases/` and `context/sample-tickets.json`. Handling strategies are implemented in
Phase 2B–2E prototype code.

### EC-001 — Non-English Message (TKT-030: Urdu, TKT-043: Spanish)

| Field | Detail |
|-------|--------|
| **Ticket** | TKT-030 (WhatsApp, Urdu/Arabic script), TKT-043 (Web Form, Spanish) |
| **Customer** | TKT-030: Pakistan customer via WhatsApp; TKT-043: Maria Garcia, solucionesMX.com |
| **Discovery** | TKT-030 detected by high non-ASCII char ratio; TKT-043 missed by heuristic (mostly ASCII Spanish) |
| **Handling** | Use language classifier (`langdetect`/`fasttext` — not ASCII ratio); agent responds in same language as customer |
| **Lesson** | ASCII-ratio heuristics miss Spanish and similar Latin-script non-English languages. Language detection must use a proper classifier. |
| **R-ref** | R4 in discovery-log.md |

---

### EC-002 — Empty / Gibberish Message (TKT-032)

| Field | Detail |
|-------|--------|
| **Ticket** | TKT-032 (WhatsApp) |
| **Handling** | Request clarification; DO NOT create a ticket; DO NOT call any tools; respond with a polite "Could you help me understand your question?" |
| **Why** | Creating a ticket for gibberish pollutes the database and triggers unnecessary tool calls |
| **R-ref** | R5 in discovery-log.md |

---

### EC-003 — Angry / Negative Sentiment Customer (TKT-001, TKT-006, TKT-015, TKT-023, TKT-026, TKT-038, TKT-041, TKT-046, TKT-057, TKT-060)

| Field | Detail |
|-------|--------|
| **Tickets** | 10 tickets with sentiment score < 0.3 threshold |
| **Handling** | Sentiment check on EVERY message; escalate when score < 0.3; first sentence MUST acknowledge frustration before any solution |
| **Escalation framing** | "I want to make sure you get the best possible help, so I'm connecting you with a specialist." — never say "the AI can't handle this" |
| **Source** | Constitution §V, Escalation Trigger #1 |

---

### EC-004 — Refund Request (TKT-007, TKT-026, False Positive TKT-003)

| Field | Detail |
|-------|--------|
| **Tickets** | TKT-007 (email, invoice INV-2026-00487), TKT-026 (WhatsApp, true refund); TKT-003 (false positive — "Will I be charged prorated?") |
| **Handling** | True refund: escalate to #billing-escalations; acknowledge receipt; provide SLA ETA |
| **Critical lesson** | TKT-003 was a false positive — the word "charged" in "Will I be charged for the full month?" is NOT a refund. Use LLM intent detection, not keyword matching |
| **R-ref** | R11 in discovery-log.md |

---

### EC-005 — Very Long Message (TKT-051: 529 words)

| Field | Detail |
|-------|--------|
| **Ticket** | TKT-051 (Web Form, 529-word engineering-grade bug report with version numbers, timestamps, error code GC-403) |
| **Handling** | Summarise to ≤ 200 words before LLM processing (token budget management); store full original message in DB for audit trail |
| **Threshold** | Messages > 400 words trigger summarisation |
| **R-ref** | R8 in discovery-log.md |

---

### EC-006 — Legal / GDPR Request (TKT-044)

| Field | Detail |
|-------|--------|
| **Ticket** | TKT-044 (Web Form, GDPR data deletion rights inquiry) |
| **Handling** | Immediate escalation; provide ZERO information about data; acknowledge only that the query is under review; no further AI response |
| **Legal trigger words** | GDPR, CCPA, data breach, lawsuit, subpoena, DPA, regulatory inquiry, data deletion rights |
| **Source** | Constitution §V, Escalation Trigger #3; `context/escalation-rules.md` §3 |

---

### EC-007 — Cross-Channel Customer: James Okonkwo

| Field | Detail |
|-------|--------|
| **Tickets** | TKT-002 (email, how-to automation setup) → TKT-052 (Web Form, "Follow up: automation still not working as expected") |
| **Email** | `james@techvault.io` |
| **Expected behavior** | Agent on TKT-052 MUST call `get_customer_history`, see TKT-002, acknowledge "I see you reached out before about automation setup — let me help further..." |
| **Failure mode** | Without cross-channel lookup, agent treats TKT-052 as first contact and gives generic setup advice already given in TKT-002 |

---

### EC-008 — Cross-Channel Customer: Marcus Thompson

| Field | Detail |
|-------|--------|
| **Tickets** | TKT-025 (WhatsApp, "Automation stopped working") → TKT-050 (Web Form, "still having Slack issues — I reached out via WhatsApp earlier") |
| **Email** | `marcus.t@buildright.co.uk` |
| **Expected behavior** | Agent on TKT-050 MUST recognise WhatsApp history and not repeat the same reconnect fix that already failed |
| **Why it matters** | This is the canonical cross-channel continuity test case. Failing it signals a broken support experience. |

---

### EC-009 — Pricing Negotiation (TKT-020, TKT-040, TKT-055)

| Field | Detail |
|-------|--------|
| **Tickets** | TKT-020 (email), TKT-040 (WhatsApp), TKT-055 (Web Form) — all ask about discounts or custom pricing |
| **Handling** | Immediate escalation to Sales/CSM team; acknowledge interest; reveal ZERO pricing strategy; no custom quotes |
| **False positive risk** | TKT-042 contains "engineering manager" — not a human-agent request. Intent-based detection required. |

---

### EC-010 — Security Incident (TKT-060)

| Field | Detail |
|-------|--------|
| **Ticket** | TKT-060 (highest-priority escalation in dataset) |
| **Handling** | Immediate escalation to `#security-incidents`; bypass all queues; do NOT ask for more details via chat (risk of leaking information); acknowledge urgency only |
| **Source** | Constitution §V, Escalation Trigger #7; `context/escalation-rules.md` §7 |

---

## 10. Architecture Decisions (ADRs)

Both ADRs are accepted and binding for the production build.

### ADR-0001 — ConversationStore Lifecycle: Singleton vs. Injectable

**File:** `history/adr/0001-conversation-store-singleton-vs-injectable.md`
**Date:** 2026-04-02 | **Status:** Accepted | **Feature:** Phase 2C

**Decision:** Module-level singleton with `get_store()` factory; `ConversationStore` remains directly
instantiable for test isolation. `process_ticket()` calls `get_store()` at entry.

**Rationale:**
- Zero import-time side effects; store initialised only on first `get_store()` call
- Test isolation without mocking: each unit test creates `ConversationStore()` directly
- Single swap point for Phase 4A PostgreSQL migration (`get_store()` is the only change point)
- Minimal diff — single `store = get_store()` line added to `process_ticket`

**Known limitations:**
- Not async-safe (acceptable for single-process prototype; Phase 4 replaces with FastAPI `Depends()`)
- Global mutable state risk if a test accidentally calls `get_store()` instead of `ConversationStore()`

**Phase 4 migration:** `get_store()` returns `PostgresConversationStore` satisfying `contracts/store_interface.py`. All 13 method signatures must be preserved exactly.

**Alternatives rejected:** Explicit DI (`store` as parameter — changes public signature, breaks 16 tests); class-level singleton (`__new__` override — breaks test isolation completely); framework DI container (overkill, adds dependency).

---

### ADR-0002 — Skill Pipeline: Synchronous Sequential Design (Phase 2E) with Async Migration Path (Phase 4)

**File:** `history/adr/0002-skill-pipeline-synchronous-vs-asynchronous-design.md`
**Date:** 2026-04-03 | **Status:** Accepted | **Feature:** Phase 2E

**Decision:** `SkillsInvoker.run()` is a plain synchronous method. All 5 skill adapters call
their target functions directly — no `await`, no event loop. Phase 4 introduces
`AsyncSkillsInvoker(SkillsInvoker)` as a subclass, overriding only `run()` and
`apply_channel_adaptation()` with `async def` equivalents.

**Rationale:**
- Zero friction for Phase 2E: 79+ existing tests run synchronously with no `pytest-asyncio`
- Smallest possible diff: thin wrappers over existing synchronous functions
- Explicit migration path: Phase 4 engineer knows exactly what changes (`async/await`) and what stays the same

**HIGH RISK flag:** `evaluate_escalation()` makes a blocking OpenAI API call. In Phase 4, this blocks the entire `asyncio` event loop per call (~500ms–2s). MUST be wrapped with `asyncio.to_thread(evaluate_escalation, message)` in `AsyncSkillsInvoker`. This is a mandatory pre-flight item for Phase 4.

**Phase 4 migration contract:**
- Keep `SkillsInvoker` (renamed `SyncSkillsInvoker`) — CLI and test reference
- `AsyncSkillsInvoker(SyncSkillsInvoker)` overrides only `run()` and `apply_channel_adaptation()`
- Kafka worker (`src/workers/ticket_worker.py`) uses `AsyncSkillsInvoker` exclusively
- All tests against `SyncSkillsInvoker` continue to pass unchanged

**Alternatives rejected:** Async-first now (`asyncio.run()` — breaks 79 tests); `ThreadPoolExecutor` (ConversationStore not thread-safe); `anyio` / `trio` (out of scope, irrelevant for `aiokafka`).

---

## 11. Production Build Map

This table maps every prototype component to its production equivalent. It is the authoritative
reference for Phase 3 (Specialization) engineering work.

| Incubation Component | File / Module | Production Equivalent | Production File |
|---------------------|---------------|----------------------|-----------------|
| Core interaction loop | `src/agent/prototype.py::process_ticket()` | OpenAI Agents SDK agent with `@function_tool` decorated tools | `agent/customer_success_agent.py` |
| MCP server tools (7 tools) | `src/mcp_server/server.py` | `@function_tool` decorated functions with Pydantic input schemas | `agent/tools.py` |
| In-memory ConversationStore | `src/agent/conversation_store.py` | Neon PostgreSQL 16 + pgvector; `asyncpg` driver | `database/queries.py` + `database/schema.sql` |
| In-memory `_ticket_index` dict | `src/mcp_server/server.py::_ticket_index` | PostgreSQL `tickets` table with FK to `conversations` | `database/schema.sql` |
| In-memory customer profiles | `ConversationStore._customers` | PostgreSQL `customers` + `customer_identifiers` tables | `database/schema.sql` |
| Knowledge base (Jaccard search) | `src/agent/knowledge_base.py` | PostgreSQL `knowledge_base` table + pgvector `ivfflat` index; cosine similarity search | `database/queries.py::search_knowledge_base()` |
| Channel formatter | `src/agent/channel_formatter.py` | Channel-aware response formatters (same logic, production-hardened) | `agent/formatters.py` |
| Escalation evaluator (LLM call) | `src/agent/escalation_evaluator.py` | Same logic; wrapped with `asyncio.to_thread()` in async context | `agent/tools.py::escalate_decision_tool()` |
| Skills invoker (sync) | `src/agent/skills_invoker.py::SkillsInvoker` | `AsyncSkillsInvoker` subclass in Kafka worker context | `workers/message_processor.py` |
| System prompt with datetime | `src/agent/prompts.py` | Same `ZoneInfo("Asia/Karachi")` injection; extracted to prompts module | `agent/prompts.py` |
| Print statement output | `prototype.py` (print to stdout) | Structured logging (`logging` → stderr) + Kafka events to `fte.metrics` topic | `workers/message_processor.py` |
| Single-threaded CLI execution | `prototype.py __main__` | Async Kubernetes worker pods (HPA min=3, max=20 for API; max=30 for workers) | `k8s/deployment-worker.yaml` |
| Hardcoded config | `.env` file only | Environment variables + Kubernetes `ConfigMap` / `Secret` objects | `k8s/configmap.yaml`, `k8s/secrets.yaml` |
| Direct channel simulation | `send_response` MCP tool (logs to stderr) | Gmail API `send_reply()` with thread ID; Twilio `send_message()` with WhatsApp prefix; FastAPI webhook handlers | `channels/gmail_handler.py`, `channels/whatsapp_handler.py` |
| Manual test runs | `pytest tests/` local | Automated pytest suite in CI + `tests/test_multichannel_e2e.py` | `tests/test_e2e.py` |
| Ticket ID (`TKT-<hex>`) | `ConversationStore` UUID generation | Same format; stored as primary key in `tickets` table | `database/schema.sql` |
| Escalation ID (`ESC-<hex>`) | `escalate_to_human` MCP tool | Same format; stored in `escalations` table with `assigned_to` FK | `database/schema.sql` |

**Required PostgreSQL tables for production (8 total):**
`customers`, `customer_identifiers`, `conversations`, `messages`, `tickets`,
`knowledge_base`, `channel_configs`, `agent_metrics`

**Required Kafka topics (9 total):**
`fte.tickets.incoming`, `fte.channels.email.inbound`, `fte.channels.whatsapp.inbound`,
`fte.channels.webform.inbound`, `fte.channels.email.outbound`,
`fte.channels.whatsapp.outbound`, `fte.escalations`, `fte.metrics`, `fte.dlq`

---

## 12. Test Coverage Summary

**Total: 101 tests passing across 7 test files** (all green on `003-mcp-server` branch as of 2026-04-04)

| Test File | Tests | Phase | What It Covers |
|-----------|-------|-------|----------------|
| `tests/unit/test_conversation_store.py` | 31 | 2C | `ConversationStore` — customer creation, conversation threading, ticket state machine transitions, sentiment trend computation, message cap enforcement, cross-channel identity, `get_store()` singleton behaviour, `reset_store()` teardown |
| `tests/unit/mcp_server/test_tools.py` | 27 | 2D | All 7 MCP tools — input validation (empty params, invalid enums), success paths, error paths, idempotency (`resolve_ticket` already-resolved), terminal state protection (`ESCALATED` cannot resolve), `get_customer_history` unknown customer, `get_sentiment_trend` no-history |
| `tests/test_skills.py` | 22 | 2E | `SkillsRegistry` lookup by `skill_id`, `SkillManifest` frozen dataclass immutability, `InvokerResult` dataclass fields, each of the 5 skill adapter methods, full pipeline `run()` execution, `apply_channel_adaptation()` for all 3 channels |
| `tests/unit/test_conversation_store.py` | — | — | (counted above in 31) |
| `tests/test_prototype.py` | 8 | 2B | `process_ticket()` core loop — email, WhatsApp, and Web Form messages; escalation path; KB result injection; datetime injection in system prompt |
| `tests/test_cross_channel.py` | 5 | 2C | Cross-channel identity unification — email→web_form (James Okonkwo pattern), WhatsApp→web_form (Marcus Thompson pattern), phone-only identity, same customer on 3 channels |
| `tests/test_core_loop.py` | 4 | 2B | Channel normalisation, message formatting per channel, category inference from message content |
| `tests/test_escalation_evaluator.py` | 4 | 2B | `evaluate_escalation()` — refund trigger, sentiment trigger, explicit human request, negative + legal combination |

**Test isolation contract:** Unit tests construct `ConversationStore()` directly (never call `get_store()`). Integration tests use `reset_store()` in teardown. This is documented in `history/adr/0001-conversation-store-singleton-vs-injectable.md`.

**Coverage gaps (Phase 3 additions required):**
- `tests/test_multichannel_e2e.py` — end-to-end channel integration tests (not yet written; required for production phase)
- Kafka producer/consumer round-trip tests
- FastAPI webhook handler tests (Gmail Pub/Sub, Twilio signature validation)
- Web Support Form Next.js component tests

---

## Appendix A — Requirements Traceability

All 14 requirements discovered in Phase 2A (discovery-log.md R1–R14) and their implementation status:

| Req | Description | Status | Implementation |
|-----|-------------|--------|----------------|
| R1 | WhatsApp customers identified by E.164 phone; attempt email resolution for cross-channel | ✅ Phase 2C | `CustomerIdentification` skill, `ConversationStore` |
| R2 | Gmail thread ID detection — replies attach to existing ticket | 🔲 Phase 4 | `channels/gmail_handler.py` (planned) |
| R3 | Response length limits strictly enforced per channel | ✅ Phase 2B | `channel_formatter.py`, `ChannelAdaptation` skill |
| R4 | Non-English detection via language classifier (not ASCII ratio) | 🔲 Phase 3 | `langdetect` / `fasttext` integration (planned) |
| R5 | Gibberish/empty messages request clarification — no ticket created | ✅ Phase 2B | `prototype.py::process_ticket()` |
| R6 | Cross-channel history fetched before every response | ✅ Phase 2C | `get_customer_history` MCP tool + `CustomerIdentification` skill |
| R7 | Web Form pre-categorisation treated as hint; agent re-classifies | ✅ Phase 2B | LLM-based category inference in `process_ticket()` |
| R8 | Messages > 400 words summarised before LLM processing | 🔲 Phase 3 | Summarisation step in production agent (planned) |
| R9 | SLA clock starts at `received_at` timestamp | ✅ Phase 2C | `Ticket.opened_at` = `received_at` from `TicketMessage` |
| R10 | Same-domain follow-up detection (nexgen-ops.com pattern) | 🔲 Phase 3 | Domain clustering logic (planned) |
| R11 | Escalation triggers LLM-intent-based, NOT keyword-based | ✅ Phase 2B | `escalation_evaluator.py` uses GPT-4o-mini intent classification |
| R12 | Security incidents bypass all queues → `#security-incidents` | ✅ Phase 2C | Escalation Trigger #7 in escalation contract |
| R13 | Pakistan market / Urdu support on roadmap | 📋 Roadmap | Not in Phase 3 scope |
| R14 | WhatsApp 24-hour conversation window for multi-message threading | ✅ Phase 2C | `ConversationStore.get_active_conversation()` |

**Legend:** ✅ Implemented in prototype | 🔲 Planned for production phase | 📋 Roadmap (post-hackathon)

---

*Spec version 1.0.0 — Ratified 2026-04-04 — Phase 2F complete*
*Authority: Supersedes all exploration notes and draft specs from Phases 2A–2E*
*Next phase: Phase 3 — Transition (specs/transition-checklist.md)*
