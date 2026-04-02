# Feature Specification: MCP Server — CRM Tool Gateway

**Feature Branch**: `003-mcp-server`  
**Created**: 2026-04-02  
**Status**: Draft  
**Phase**: 2D

---

## Overview

Expose the NexaFlow AI Customer Success agent's capabilities as a discoverable, callable tool set through a standard protocol interface. Any AI agent — including the prototype itself, future orchestrators, and evaluation harnesses — can invoke these tools without knowing the underlying implementation.

The server must expose **7 tools minimum** and satisfy the GIAIC Hackathon 5 Exercise 1.4 requirement of at least 5 MCP tools.

---

## User Scenarios & Testing

### User Story 1 — AI Agent Searches Knowledge Base (Priority: P1)

An AI agent handling a support ticket needs to find relevant product documentation before composing a reply. It calls the knowledge search tool and receives ranked document excerpts to incorporate into its answer.

**Why this priority**: Underpins every ticket response — if knowledge retrieval fails, the agent cannot deliver accurate answers.

**Independent Test**: Call the knowledge search tool with a product-related query and confirm ranked results are returned with relevance scores.

**Acceptance Scenarios**:

1. **Given** a valid text query, **When** the search tool is invoked, **Then** the tool returns at least one ranked document excerpt with a relevance score greater than zero.
2. **Given** a query that matches no documents, **When** the search tool is invoked, **Then** the tool returns an empty result set (not an error).
3. **Given** a query with special characters or very long text, **When** the search tool is invoked, **Then** the tool handles it gracefully and returns a result or empty list.

---

### User Story 2 — AI Agent Creates a Support Ticket (Priority: P1)

When a new inbound message arrives, the AI agent needs to register it as a trackable support ticket so the customer's issue is persisted and can be followed up.

**Why this priority**: Ticket creation is the entry point for every customer interaction — without it, no subsequent operations (escalation, resolution) are possible.

**Independent Test**: Call `create_ticket` with valid inputs and verify a ticket ID is returned; then call `get_customer_history` to confirm the ticket appears.

**Acceptance Scenarios**:

1. **Given** valid customer ID, issue description, priority, and channel, **When** `create_ticket` is called, **Then** a unique ticket ID is returned.
2. **Given** an unknown customer ID, **When** `create_ticket` is called, **Then** a new customer profile is created and the ticket ID is returned.
3. **Given** an invalid channel value, **When** `create_ticket` is called, **Then** the tool returns a descriptive error without crashing.

---

### User Story 3 — AI Agent Retrieves Full Customer History (Priority: P2)

Before responding to a returning customer, the agent fetches all prior interactions across email, WhatsApp, and web form to provide context-aware support and avoid asking for information already given.

**Why this priority**: Cross-channel context prevents repetitive questions and is a key differentiator of the CRM agent; demonstrates Phase 2C memory integration.

**Independent Test**: Create multiple tickets across different channels for one customer, then call `get_customer_history` and confirm all channels appear in the response.

**Acceptance Scenarios**:

1. **Given** a customer with tickets from two or more channels, **When** `get_customer_history` is called, **Then** the response includes interactions from all channels with timestamps.
2. **Given** a customer ID with no prior history, **When** `get_customer_history` is called, **Then** an empty history object is returned (not an error).
3. **Given** an invalid or malformed customer ID, **When** `get_customer_history` is called, **Then** the tool returns a clear not-found result.

---

### User Story 4 — AI Agent Escalates a Ticket to Human (Priority: P2)

When the AI detects a ticket that exceeds its confidence threshold, violates an SLA, or involves enterprise-tier anger/threats, it calls the escalation tool to hand the case to a human agent and record the reason.

**Why this priority**: Escalation is the safety valve — it prevents the AI from mishandling sensitive cases and is a hackathon-required capability.

**Independent Test**: Create a ticket and call `escalate_to_human` with a reason; confirm an escalation ID is returned and the ticket status changes to ESCALATED.

**Acceptance Scenarios**:

1. **Given** an existing open ticket and a reason string, **When** `escalate_to_human` is called, **Then** an escalation ID is returned and the ticket is marked escalated.
2. **Given** a ticket ID that does not exist, **When** `escalate_to_human` is called, **Then** the tool returns a not-found error.
3. **Given** a ticket already escalated, **When** `escalate_to_human` is called again, **Then** the tool returns an idempotent result or a descriptive error.

---

### User Story 5 — AI Agent Sends a Response to the Customer (Priority: P1)

After crafting a reply, the agent dispatches it through the appropriate channel (email, WhatsApp, or web form) and records the delivery outcome against the ticket.

**Why this priority**: Sending the response is the agent's core deliverable — without it, the customer never receives help.

**Independent Test**: Create a ticket, then call `send_response` and verify the delivery status returned includes channel, timestamp, and success/failure indicator.

**Acceptance Scenarios**:

1. **Given** an existing ticket, a message body, and a supported channel, **When** `send_response` is called, **Then** a delivery status object is returned with channel and timestamp.
2. **Given** an unsupported channel value, **When** `send_response` is called, **Then** the tool returns a clear validation error.
3. **Given** an empty message body, **When** `send_response` is called, **Then** the tool rejects the call with a validation error.

---

### User Story 6 — AI Agent Checks Customer Sentiment Trend (Priority: P3)

Before deciding how urgently to respond, the agent checks whether a customer's sentiment has been worsening over recent interactions. If the trend shows deterioration, the tool recommends proactive escalation.

**Why this priority**: Value-add enhancement that improves proactive quality; demonstrates memory analytics capability from Phase 2C.

**Independent Test**: Create multiple messages with varying negative sentiment for one customer, then call `get_sentiment_trend` and confirm the trend label reflects the pattern.

**Acceptance Scenarios**:

1. **Given** a customer with multiple recorded interactions, **When** `get_sentiment_trend` is called, **Then** the response includes a trend label (improving/stable/deteriorating) and a recommendation.
2. **Given** a customer with fewer than three interactions, **When** `get_sentiment_trend` is called, **Then** the tool returns a "insufficient data" trend label with no escalation recommendation.
3. **Given** a customer showing deteriorating sentiment, **When** `get_sentiment_trend` is called, **Then** the response explicitly recommends escalation.

---

### User Story 7 — AI Agent Resolves a Ticket (Priority: P2)

After confirming the customer's issue is addressed, the agent closes the ticket with a resolution summary so the case is marked complete and the summary is stored for future context.

**Why this priority**: Clean ticket closure completes the support lifecycle and enables accurate resolution-rate reporting.

**Independent Test**: Create a ticket, then call `resolve_ticket` with a summary; confirm the ticket status is RESOLVED and the summary is stored.

**Acceptance Scenarios**:

1. **Given** an open or pending ticket and a non-empty resolution summary, **When** `resolve_ticket` is called, **Then** the ticket is marked RESOLVED and a confirmation object is returned.
2. **Given** an already-resolved ticket, **When** `resolve_ticket` is called, **Then** the tool returns an idempotent confirmation (no duplicate state change).
3. **Given** a missing or empty resolution summary, **When** `resolve_ticket` is called, **Then** the tool rejects the call with a validation error.

---

### Edge Cases

- What happens when the in-memory store is empty (fresh server start) and all tools are called? Each must return sensible empty results, not crashes.
- How does the server handle concurrent tool invocations? The in-memory store must not corrupt state under sequential rapid calls.
- What happens when the OpenAI API key is missing at server start? The server must boot and serve non-AI tools; AI-dependent tools return a clear configuration-error message.
- What happens when a tool receives a `None` or null value for a required parameter? The tool must return a validation error, not raise an unhandled exception.

---

## Requirements

### Functional Requirements

- **FR-001**: The MCP server MUST expose exactly 7 named tools discoverable via the standard protocol tool-listing interface.
- **FR-002**: The server MUST expose `search_knowledge_base(query: str)` returning a ranked list of relevant document excerpts with relevance scores.
- **FR-003**: The server MUST expose `create_ticket(customer_id: str, issue: str, priority: str, channel: str)` returning a unique ticket identifier.
- **FR-004**: The server MUST expose `get_customer_history(customer_id: str)` returning all past interactions across every channel for that customer.
- **FR-005**: The server MUST expose `escalate_to_human(ticket_id: str, reason: str)` returning an escalation identifier and updating the ticket status.
- **FR-006**: The server MUST expose `send_response(ticket_id: str, message: str, channel: str)` returning a delivery status record.
- **FR-007**: The server MUST expose `get_sentiment_trend(customer_id: str)` returning a trend label, recent sentiment scores, and a recommendation flag.
- **FR-008**: The server MUST expose `resolve_ticket(ticket_id: str, resolution_summary: str)` returning a confirmation with final ticket state.
- **FR-009**: Each tool MUST include a human-readable description and parameter schema so AI clients can discover and invoke tools without additional documentation.
- **FR-010**: The server MUST delegate all business logic to existing modules — it MUST NOT reimplement knowledge search, conversation storage, or escalation evaluation.
- **FR-011**: All tools MUST return structured, serialisable responses (no raw Python objects).
- **FR-012**: Tools that receive invalid parameter values MUST return a descriptive error result rather than raising an unhandled exception.
- **FR-013**: The server MUST be runnable from the project root via a single command and support both `stdio` transport (for local Claude Desktop / CLI use) and programmatic launch for tests.

### Key Entities

- **Tool**: A named, schema-described capability the server exposes; has a name, description, parameter schema, and return schema.
- **Ticket**: A support case record with ID, status (open/pending/escalated/resolved), channel, customer reference, and optional resolution summary.
- **Customer Profile**: A cross-channel identity with a stable key, name, linked email/phone, and ordered history of conversations.
- **Conversation**: A channel-scoped sequence of messages within a customer profile; carries a sentiment score series.
- **Delivery Status**: A record confirming or denying that a response was dispatched; includes channel, timestamp, and success flag.
- **Escalation Record**: A record of a human-escalation event; carries escalation ID, ticket ID, reason, and timestamp.
- **Sentiment Trend**: A derived view over the last N sentiment scores; carries a label (improving/stable/deteriorating) and recommendation flag.
- **KB Result**: A document excerpt returned by knowledge search; carries section title, content snippet, and relevance score.

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: All 7 tools are discoverable and invocable by a standard MCP client without additional configuration beyond server startup.
- **SC-002**: Each tool call returns a structured response within 5 seconds under normal conditions (excluding external AI API latency).
- **SC-003**: The 5 hackathon-required tools (search, create, history, escalate, send) pass end-to-end invocation tests with valid inputs.
- **SC-004**: All 7 tools return descriptive error results (not crashes) when given invalid or missing inputs.
- **SC-005**: Server startup succeeds in under 3 seconds on the development machine; tool listing is available immediately after startup.
- **SC-006**: No existing passing tests (52/52 from Phase 2C) are broken by adding the MCP server layer.
- **SC-007**: A single MCP client session can call all 7 tools in sequence and maintain consistent state throughout (tickets created remain queryable for the server's lifetime).

---

## Assumptions

- The in-memory `ConversationStore` singleton from Phase 2C is shared between the MCP server and any co-located agent process — state is not persisted to disk.
- The `send_response` tool simulates delivery (logs the message and returns a success status) since real channel integrations (Gmail, Twilio) are out of scope until Phase 4.
- Sentiment scores are derived from the existing `compute_sentiment_trend` method in `ConversationStore`; the MCP tool wraps it without modification.
- Priority values accepted by `create_ticket` are: `low`, `medium`, `high`, `critical` — matching the existing escalation evaluator's urgency vocabulary.
- The MCP server is single-process and single-threaded for Phase 2D; concurrency is out of scope.
- Authentication and transport security for the MCP server are out of scope for Phase 2D (local development only).

---

## Out of Scope

- Persistent storage (PostgreSQL, pgvector) — deferred to Phase 4A.
- Real email/WhatsApp delivery — `send_response` is simulated.
- HTTP/SSE transport — only `stdio` transport is required for Phase 2D.
- Multi-tenant isolation or API key auth on the MCP server.
- Rate limiting or quota enforcement on tool calls.

---

## Dependencies

- Phase 2B deliverable: `src/agent/knowledge_base.py` (KnowledgeBase, search), `src/agent/prototype.py` (process_ticket)
- Phase 2C deliverable: `src/agent/conversation_store.py` (ConversationStore, get_store), `src/agent/escalation_evaluator.py`
- Phase 2C deliverable: `src/agent/models.py` (Channel, TicketStatus, SentimentLabel, all dataclasses)
- Official MCP Python SDK (`mcp` package from modelcontextprotocol)
- OpenAI API key (for `escalate_to_human` which may invoke the evaluator; other tools work without it)
