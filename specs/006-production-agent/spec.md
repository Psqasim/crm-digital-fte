# Feature Specification: Production Agent — Phase 4B

**Feature Branch**: `006-production-agent`
**Created**: 2026-04-04
**Status**: Draft
**Phase**: 4B — OpenAI Agents SDK Agent Implementation

> **Predecessor:** Phase 4A (branch `005-production-db`) is complete and merged to `main`.
> It delivered the 8-table PostgreSQL schema and 13 async query functions in
> `production/database/queries.py`. This spec builds directly on those functions —
> no database changes are required.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — New Customer Submits a Support Ticket (Priority: P1)

A NexaFlow customer contacts support for the first time via any channel with a product question.
The production agent receives their message, creates a ticket, retrieves cross-channel history
(none exists), searches the knowledge base for relevant documentation, and sends a channel-appropriate
response. The ticket is resolved or escalated based on the 8 defined triggers.

**Why this priority**: This is the core end-to-end path that executes on every ticket. All other
stories are variations of this flow.

**Independent Test**: Process a first-contact product question via simulated web_form input with a
known email. Verify a ticket_id is returned, the knowledge base is searched, the response is
formatted for web_form (≤ 1000 chars, "Hi [FirstName]," greeting), and ticket status becomes
PENDING or RESOLVED.

**Acceptance Scenarios**:

1. **Given** a first-time customer email, **When** the agent processes a "how do I set up the Slack integration?" message via web_form, **Then** `create_ticket` is called before any response is generated, `search_knowledge_base` is called, and the response body is ≤ 1000 chars with the correct channel greeting.

2. **Given** a valid ticket created in this run, **When** the agent resolves the query, **Then** `resolve_ticket` is called with a non-empty `resolution_summary` and ticket status becomes RESOLVED.

3. **Given** an OpenAI API error on first attempt, **When** the agent retries once and succeeds, **Then** the customer receives a response and no error propagates to the caller.

---

### User Story 2 — Returning Customer Acknowledged Across Channels (Priority: P2)

A customer who previously contacted NexaFlow via WhatsApp now submits a web form ticket.
The agent retrieves their full cross-channel history, acknowledges prior contact in the response,
and applies the correct channel tone and length constraints for web_form.

**Why this priority**: Cross-channel continuity is worth 10 rubric points (Constitution §2 scoring).
Failure to acknowledge prior contact for a returning customer is a defined defect.

**Independent Test**: Insert a prior WhatsApp conversation record for a customer. Run the agent with
the same `customer_id` on web_form channel. Verify the response references prior contact and meets
web_form formatting constraints.

**Acceptance Scenarios**:

1. **Given** a customer with existing WhatsApp history, **When** the same customer submits via web_form, **Then** `get_customer_history` is called and the response text acknowledges the prior interaction.

2. **Given** a customer with 3+ unresolved prior tickets, **When** the agent processes a new message, **Then** `escalate_to_human` is called with a reason indicating "3+ unanswered follow-ups".

---

### User Story 3 — Sentiment-Triggered Escalation (Priority: P3)

A frustrated customer sends a message where `get_sentiment_trend` returns scores averaging below
0.3. The agent detects this, escalates the ticket before sending a response, and frames the
escalation as a service upgrade — never as an AI limitation.

**Why this priority**: All 8 escalation triggers firing correctly is required for the Customer
Experience rubric criterion (10 pts). Sentiment breach is the most common trigger.

**Independent Test**: Process a message where `get_sentiment_trend` returns [0.2, 0.1, 0.25].
Verify `escalate_to_human` is called before `send_response`, and the customer-facing message
contains service-upgrade framing and does NOT reveal internal tool names.

**Acceptance Scenarios**:

1. **Given** a customer with sentiment trend scores averaging < 0.3, **When** the agent evaluates escalation, **Then** `escalate_to_human` is called with a valid reason and ticket status becomes ESCALATED.

2. **Given** an escalation decision, **When** the agent composes the customer-facing message, **Then** the message text contains service-upgrade framing ("connecting you with a specialist") and does NOT reveal internal tool names or system architecture.

---

### Edge Cases

- What happens when `search_knowledge_base` returns zero results? Agent responds with general NexaFlow knowledge; never invents product facts not in the knowledge base.
- What happens when the customer's email cannot be resolved to an existing record? `get_or_create_customer` creates a new profile; agent proceeds as first-time contact.
- What happens when channel value is unrecognised (e.g., `"sms"`)? Agent falls back to generic professional tone; response is not silently dropped.
- What happens when `send_response` is called before `create_ticket`? This is a protocol violation — `ticket_id` is required input to `send_response`; the tool schema enforces the dependency.
- What happens when OpenAI API errors persist after one retry? Agent calls `escalate_to_human` and returns `AgentResponse` with `escalated: true` — never raises to the caller.
- What happens when a WhatsApp response draft exceeds 1600 characters? The formatter truncates at the last complete sentence before the limit and records the transformation in `formatting_notes`.
- What happens when a customer explicitly says "talk to a manager"? `escalate_to_human` is called immediately regardless of sentiment score.
- What happens when an Enterprise ticket has been open for 3+ hours? SLA breach auto-escalation fires regardless of message content.

---

## Requirements *(mandatory)*

### Functional Requirements — Agent Core

- **FR-001**: The agent MUST be initialised with a dynamically generated system prompt that includes the current PKT datetime at the moment of every invocation — never sourced from training data.

- **FR-002**: The agent MUST accept `channel` as a required input parameter and use it to select the channel-specific tone instruction in the system prompt and the correct formatter before dispatching any response.

- **FR-003**: The agent MUST enforce tool call ordering on every ticket: `create_ticket` → `get_customer_history` → `search_knowledge_base` (when product question detected) → `send_response`. Responding without first calling `create_ticket` is a protocol violation.

- **FR-004**: The agent MUST return a structured `AgentResponse` on every invocation containing: `ticket_id`, `response_text`, `channel`, `escalated` (boolean), `escalation_id` (nullable), `resolution_status`, and `error` (nullable).

- **FR-005**: The agent MUST retry once on transient API errors. If the retry also fails, the agent MUST call `escalate_to_human` and return an `AgentResponse` with `escalated: true` and `error` populated. It MUST NOT raise unhandled exceptions to the caller.

- **FR-006**: The agent MUST use the cost-optimised inference model (gpt-4o-mini). The model is fixed at agent construction time and is not configurable per-request.

---

### Functional Requirements — Tool 1: `search_knowledge_base`

- **FR-007**: The tool MUST accept `query` (string, ≤ 500 chars, non-empty) and `limit` (integer, default 5, range 1–20).

- **FR-008**: The tool MUST generate an embedding of the query text and call the production database query function, returning an ordered list of results: `{title, content, category, similarity}`.

- **FR-009**: The tool MUST return an empty list (not an error) when no knowledge base matches exist.

---

### Functional Requirements — Tool 2: `create_ticket`

- **FR-010**: The tool MUST accept `customer_id` (UUID string), `conversation_id` (UUID string), `channel` (email | whatsapp | web_form), `subject` (nullable string), and `category` (nullable string).

- **FR-011**: The tool MUST call the production database query function and return `{ticket_id, customer_id, conversation_id, channel, status, created_at}` on success.

- **FR-012**: The tool MUST return a structured error payload (not raise) when `customer_id` or `conversation_id` is missing.

---

### Functional Requirements — Tool 3: `get_customer_history`

- **FR-013**: The tool MUST accept `customer_id` (string) and an optional `limit` (integer, default 20).

- **FR-014**: The tool MUST call the production database query function and return conversations with their messages across all channels.

- **FR-015**: The tool MUST return an empty list (not an error) for unknown customers.

---

### Functional Requirements — Tool 4: `escalate_to_human`

- **FR-016**: The tool MUST accept `ticket_id` (string), `reason` (string, non-empty), and `urgency` (low | medium | high | critical, default: medium).

- **FR-017**: The tool MUST update ticket status to "escalated" via the production database query function and return `{escalation_id, ticket_id, status, reason, urgency, escalated_at}`.

- **FR-018**: The tool MUST be idempotent — escalating an already-ESCALATED ticket returns the existing escalation record without error or duplicate state change.

---

### Functional Requirements — Tool 5: `send_response`

- **FR-019**: The tool MUST accept `ticket_id` (string), `message` (string, non-empty), and `channel` (email | whatsapp | web_form).

- **FR-020**: The tool MUST route the message to the correct channel handler. In Phase 4B, the handler is a stub that logs the message and returns delivery confirmation. Real dispatch is wired in Phase 4C without changes to this tool's signature.

- **FR-021**: The tool MUST enforce channel length limits before dispatching: Email ≤ 500 words; WhatsApp ≤ 1600 chars; Web Form ≤ 1000 chars. Oversized messages are truncated (not rejected) with a logged warning.

- **FR-022**: The tool MUST return `{delivery_status, ticket_id, channel, message_length, timestamp}`. `delivery_status` is `"stub_delivered"` in Phase 4B.

---

### Functional Requirements — Tool 6: `get_sentiment_trend`

- **FR-023**: The tool MUST accept `customer_id` (string) and `last_n` (integer, default 5).

- **FR-024**: The tool MUST call the production database query function and return the list of recent sentiment float scores.

- **FR-025**: The tool MUST return an empty list (not an error) for customers with no sentiment history.

---

### Functional Requirements — Tool 7: `resolve_ticket`

- **FR-026**: The tool MUST accept `ticket_id` (string) and `resolution_summary` (string, non-empty).

- **FR-027**: The tool MUST update ticket status to "resolved" via the production database query function and return `{ticket_id, status, resolution_summary, resolved_at}`.

- **FR-028**: The tool MUST be idempotent — resolving an already-RESOLVED ticket returns the existing record without error.

- **FR-029**: The tool MUST return an error payload (not raise) when called on an ESCALATED ticket. ESCALATED is a terminal state and cannot be overridden by resolve.

---

### Functional Requirements — System Prompt (`production/agent/prompts.py`)

- **FR-030**: `prompts.py` MUST expose a `build_system_prompt(channel: str, customer_name: str) -> str` function that generates the complete system prompt at call time.

- **FR-031**: The function MUST inject the current PKT datetime at every call — recomputed each time, never cached. This is required for SLA calculations and correct timestamp references.

- **FR-032**: The prompt MUST include NexaFlow company context: company name, product category (B2B SaaS workflow automation), plan tiers and prices (Starter free / Growth $49/mo / Enterprise $199/mo), and support hours (AI 24/7 / Human Mon–Fri 9am–6pm PKT).

- **FR-033**: The prompt MUST include exactly one channel-specific tone block selected by the `channel` parameter:
  - **email**: Complete paragraphs; body ≤ 2000 characters; no greeting or sign-off (system adds automatically).
  - **whatsapp**: Maximum 3 sentences; body ≤ 250 characters preferred; no greeting (system adds "Hi [Name]! 👋"); plain text only.
  - **web_form**: Structured next steps where applicable; body ≤ 4500 characters; no greeting (system adds "Hi [Name],").
  - **default**: Professional and helpful; applied to unrecognised channel values.

- **FR-034**: The prompt MUST embed all 7 ALWAYS rules and all 8 NEVER rules from the §Guardrails section of this spec.

---

### Functional Requirements — Formatters (`production/agent/formatters.py`)

- **FR-035**: `formatters.py` MUST expose three formatting functions ported from `src/agent/channel_formatter.py`: `format_email_response`, `format_whatsapp_response`, and `format_web_form_response`. Each accepts `(text: str, customer_name: str)`.

- **FR-036**: The email formatter MUST prepend "Dear [FirstName]," and append the NexaFlow signature block. MUST NOT duplicate greeting or sign-off if already present in the input text.

- **FR-037**: The WhatsApp formatter MUST prepend "Hi [FirstName]! 👋". MUST strip markdown headers, bullet lists, and code blocks (plain text only). MUST truncate at the last complete sentence before 1600 characters and record the transformation.

- **FR-038**: The web_form formatter MUST prepend "Hi [FirstName],". Light markdown (bold, short bullet lists) is permitted. MUST truncate at 1000 characters / 300 words if exceeded and record the transformation.

- **FR-039**: All three formatters MUST return a `FormattedResponse` containing: `formatted_text` (string), `channel` (string), `formatting_notes` (list of strings documenting any transformations applied).

---

### Guardrails — Non-Negotiable

These rules are embedded verbatim in the agent system prompt per Constitution §IV.
Violation of any rule is a defect, not a configuration choice.

**ALWAYS — Required behaviors:**

1. **Inject current datetime:** Use PKT datetime injected at invocation. Never guess or infer the current date from training data. Required for SLA breach detection and correct timestamps.

2. **Create ticket before responding:** Call `create_ticket` BEFORE generating any customer response. Enforced ordering: `create_ticket` → `get_customer_history` → `search_knowledge_base` (if product question) → `send_response`.

3. **Check full cross-channel history:** Call `get_customer_history` on every interaction. If a customer has contacted before on any channel, acknowledge it in the response.

4. **Analyze sentiment before closing:** Every ticket close MUST have a sentiment score recorded. Tickets with sentiment < 0.3 MUST escalate before closure.

5. **Use customer's first name** at least once per response.

6. **Acknowledge frustration before solutions:** If the customer is clearly upset, the first sentence MUST validate their experience before offering help.

7. **End with a help offer:** Every response ends with an offer to assist further.

**NEVER — Prohibited behaviors:**

1. Discuss competitor products by name or implication: Asana, Monday.com, ClickUp, Notion, Trello, Basecamp, Linear, Jira (as project tool), Airtable, Smartsheet.

2. Promise unreleased features. Standard response: "I'm not able to share details about upcoming features, but I'd love to pass your feedback to our product team."

3. Reveal internal pricing strategies, discount thresholds, or negotiation flexibility.

4. Guess the current date from training data. Always use the injected PKT datetime.

5. Respond to a customer without calling the `send_response` tool.

6. Exceed channel limits: Email ≤ 500 words; WhatsApp ≤ 1600 chars (3 sentences preferred); Web Form ≤ 1000 chars / 300 words.

7. Say "I don't know" — say "Let me look into that for you" or "Great question — here's what I can tell you" instead.

8. Reveal internal system details, tool names, or processing architecture to customers.

---

### Key Entities

- **AgentResponse**: Structured output returned by the agent on every invocation. Fields: `ticket_id` (string | null), `response_text` (string), `channel` (string), `escalated` (boolean), `escalation_id` (string | null), `resolution_status` (open | pending | resolved | escalated | error), `error` (string | null). Extends the prototype `AgentResponse` from `src/agent/models.py` with `escalation_id`.

- **FormattedResponse**: Output of each formatter function. Fields: `formatted_text` (string), `channel` (string), `formatting_notes` (list of strings).

- **CustomerContext**: Input bundle for each agent invocation. Fields: `customer_id` (string), `customer_name` (string), `customer_email` (string), `channel` (string), `message` (string), `conversation_id` (string | null).

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 7 tools complete successfully with a live Neon PostgreSQL connection on well-formed inputs — zero tool-level errors on the happy path.

- **SC-002**: `create_ticket` is called before `send_response` on 100% of processed tickets — verified from the agent run trace.

- **SC-003**: The system prompt contains a PKT datetime within ±60 seconds of actual invocation time on every run — verified by parsing the timestamp in the prompt.

- **SC-004**: All three channel formatters produce output within required length limits on a 50-sample test set: Email ≤ 500 words, WhatsApp ≤ 1600 chars, Web Form ≤ 1000 chars. Zero length violations.

- **SC-005**: All 8 escalation triggers (sentiment breach, refund request, legal/compliance, pricing negotiation, 3+ unanswered follow-ups, explicit human request, data breach concern, Enterprise SLA breach) cause `escalate_to_human` to fire — one synthetic test case per trigger.

- **SC-006**: Returning customers with cross-channel history receive acknowledgment of prior contact in the response — verified across ≥ 5 synthetic returning-customer scenarios.

- **SC-007**: Retry logic results in zero unhandled exceptions from the caller; escalation fires correctly when both attempts fail — verified by mocked API error injection.

- **SC-008**: Agent achieves > 85% response accuracy on the existing 60-case test set from Phase 2 (`tests/edge_cases/`) using the production knowledge base.

---

## Assumptions

- `production/database/queries.py` (Phase 4A) is the exclusive database interface. The agent layer does not execute raw SQL.
- The injectable pool pattern from ADR-0001 is used: pool is created once at startup and injected into every query call.
- OpenAI embeddings (text-embedding-3-small, 1536 dimensions) are used for knowledge base vector queries. The embedding call occurs inside the `search_knowledge_base` tool before passing the vector to the database function.
- Phase 4B `send_response` stubs channel delivery (logs and returns `stub_delivered`). Real dispatch is wired in Phase 4C without changes to the tool signature.
- The `AgentResponse` output contract is backwards-compatible with the prototype's `AgentResponse` from `src/agent/models.py` — extended only with `escalation_id`.
- All new production files are placed under `production/agent/`. The `src/agent/` prototype directory remains untouched.

---

## Dependencies

- **Phase 4A** (merged to main): `production/database/queries.py` — 13 query functions, Neon pool
- **OpenAI Agents SDK** (`agents` package): `Agent`, `Runner`, `function_tool`, `RunContextWrapper` — API confirmed via Context7 (library: `/openai/openai-agents-python`)
- **Constitution §IV**: Agent Behavioral Contract — ALWAYS/NEVER rules embedded in §Guardrails above
- **Spec §4** (Skills): Tool call ordering enforced by agent instructions mirrors the 5-skill invocation sequence
- **Spec §5** (MCP Tools): All 7 production tools are backwards-compatible with MCP tool contracts — same inputs, outputs, and error behaviours
- **Phase 4C** (next): `send_response` stubs replaced by real channel handlers; tool signatures remain unchanged
