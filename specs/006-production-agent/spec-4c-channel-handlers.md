# Feature Specification: Phase 4C — Gmail & WhatsApp Channel Handlers

**Feature Branch**: `006-production-agent`
**Created**: 2026-04-04
**Status**: Draft
**Phase**: 4C-i (Gmail Handler) + 4C-ii (WhatsApp Handler)

> **Predecessor:** Phase 4B is complete. The production agent (`production/agent/`) has 7
> `@function_tool` functions and 122 passing tests. The `send_response` tool currently logs
> to stderr (stub). This spec makes `send_response` real by wiring two channel handlers that
> receive inbound messages and dispatch outbound replies.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Email Received, Ticket Queued, Reply Sent (Priority: P1)

A NexaFlow customer sends an email to the support address. The Gmail handler receives the
Pub/Sub push notification, fetches the full message from Gmail, normalises it into the
unified ticket format, pushes it to the email Kafka topic, and dispatches a threaded reply
via Gmail API so the customer receives the response in the same email thread.

**Why this priority**: Email is the highest-volume channel (~50% of 800 tickets/week) and
the Gmail handler is the most complex due to the two-step Pub/Sub → history.list flow.
Failure here breaks ticket intake entirely for email.

**Independent Test**: POST a synthetic Pub/Sub notification payload to the webhook endpoint.
Assert: (a) a TicketMessage record lands on `tickets.email` with `channel="email"`, (b) the
Gmail API `send` method was called with the correct `threadId`, (c) the webhook returns HTTP 200.

**Acceptance Scenarios**:

1. **Given** a valid Pub/Sub push notification with a base64url-encoded payload, **When** the
   webhook endpoint receives it, **Then** the handler decodes the payload, calls `history.list`
   to fetch the actual message, and normalises sender email, subject, body, and thread_id into
   a TicketMessage with `channel="email"`.

2. **Given** a TicketMessage constructed from a Gmail message, **When** the handler publishes to
   Kafka, **Then** the message appears on the `tickets.email` topic within 2 seconds.

3. **Given** the agent has generated a response text, **When** `send_response` is called with
   `channel="email"`, **Then** the reply is sent via Gmail API using the original `thread_id` so
   the customer sees it as a reply in their existing email thread.

4. **Given** the same Gmail `message_id` arrives twice (Pub/Sub at-least-once delivery), **When**
   the handler receives the duplicate, **Then** the second delivery is silently dropped and no
   duplicate TicketMessage is produced.

---

### User Story 2 — WhatsApp Message Received, Ticket Queued, Reply Sent (Priority: P1)

A NexaFlow customer sends a WhatsApp message via Twilio Sandbox. The WhatsApp handler
validates the Twilio webhook signature, extracts the message content, normalises it into the
unified ticket format, pushes it to the WhatsApp Kafka topic, and replies via the Twilio
Messages API.

**Why this priority**: WhatsApp is the second-largest channel. Signature validation failure
creates a security gap; missing deduplication creates duplicate tickets. Both are P1 defects.

**Independent Test**: POST a synthetic Twilio webhook payload with a valid `X-Twilio-Signature`
header to the handler endpoint. Assert: (a) a TicketMessage lands on `tickets.whatsapp` with
`channel="whatsapp"`, (b) Twilio's `messages.create` was called with the customer's `From`
number as `to`, (c) the webhook returns HTTP 200.

**Acceptance Scenarios**:

1. **Given** a Twilio webhook POST with a valid `X-Twilio-Signature` header, **When** the handler
   receives it, **Then** signature validation passes and the message is processed normally.

2. **Given** a Twilio webhook POST with an invalid or missing `X-Twilio-Signature` header, **When**
   the handler receives it, **Then** it returns HTTP 403 and no TicketMessage is produced.

3. **Given** a valid WhatsApp message with a non-empty `Body`, **When** the handler processes it,
   **Then** a TicketMessage is produced with `channel="whatsapp"`, `customer_phone` set to the
   E.164 `From` number, and `message` set to the `Body` text.

4. **Given** a WhatsApp message containing media attachments (images, audio, etc.) but no text
   body, **When** the handler receives it, **Then** the message body is treated as empty and the
   handler produces a TicketMessage with a placeholder body (e.g., "[media attachment]") — the
   endpoint does not crash.

5. **Given** the same `MessageSid` arrives twice, **When** the handler processes the second
   delivery, **Then** the duplicate is silently dropped and only one TicketMessage is produced.

6. **Given** the agent has generated a reply text, **When** `send_response` is called with
   `channel="whatsapp"`, **Then** the reply is sent via Twilio Messages API to the customer's
   `From` number from the NexaFlow Twilio WhatsApp number.

---

### User Story 3 — Handler Fault Isolation (Priority: P2)

Any error in either channel handler (malformed payload, Gmail API timeout, Twilio API
error, Kafka unavailability) is logged to stderr but never causes the webhook endpoint to
return a 5xx response that would trigger Pub/Sub or Twilio retry storms.

**Why this priority**: Pub/Sub retries on non-200/204 responses; Twilio retries on 5xx.
An unhandled exception that propagates as a 500 would cause runaway redelivery. Fault
isolation protects the system from amplification during partial failures.

**Independent Test**: Force a Kafka publish failure (mock the producer). Assert the webhook
still returns HTTP 200, the error is logged to stderr, and no exception propagates.

**Acceptance Scenarios**:

1. **Given** the Kafka producer is unavailable, **When** either handler attempts to publish,
   **Then** the error is logged and the webhook returns HTTP 200 (message is lost, not
   retried — acceptable trade-off for hackathon; Redis dead-letter queue is a production TODO).

2. **Given** the Gmail history.list API call returns an error, **When** the Gmail handler
   processes the notification, **Then** the error is logged to stderr and the webhook returns
   HTTP 200.

3. **Given** an entirely malformed JSON body is POSTed to either webhook endpoint, **When**
   the handler receives it, **Then** it returns HTTP 400 (not 500) and logs the parse error.

---

### Edge Cases

- Pub/Sub notification where `historyId` returns zero new messages in `history.list` (e.g.,
  a label-change event rather than a new message) — handler exits cleanly with no TicketMessage.
- Gmail message with no plain-text body part (HTML-only email) — handler extracts text from
  the HTML part or uses subject as body fallback.
- WhatsApp `Body` containing only whitespace — treated as empty body; placeholder used.
- Gmail OAuth token expiry — error logged; no crash; reconnect on next notification.
- Twilio `From` number not in E.164 format — normalise by stripping non-digit characters;
  log a warning; do not discard the message.
- Very large email body (>10,000 chars) — truncated to 4,000 chars before Kafka publish
  to stay within TicketMessage size expectations.

---

## Requirements *(mandatory)*

### Functional Requirements

**Gmail Handler (`production/channels/gmail_handler.py`)**

- **FR-GH-001**: The handler MUST expose a POST webhook endpoint that accepts Gmail Pub/Sub
  push notifications in the format `{"message": {"data": "<base64url>", "messageId": "..."},
  "subscription": "..."}`.
- **FR-GH-002**: The handler MUST decode the base64url `message.data` field to extract
  `emailAddress` and `historyId`, then call the Gmail API `history.list` method to retrieve
  the actual new messages since the last known historyId.
- **FR-GH-003**: For each new Gmail message, the handler MUST extract: sender email address
  (from `From` header), subject (from `Subject` header), plain-text body, and `threadId`.
- **FR-GH-004**: The handler MUST normalise each extracted Gmail message into a `TicketMessage`
  with `channel="email"`, populating `id`, `customer_email`, `subject`, `message`, `received_at`,
  and `metadata["thread_id"]`.
- **FR-GH-005**: The handler MUST publish each `TicketMessage` to the Kafka topic `tickets.email`.
- **FR-GH-006**: The handler MUST send replies via the Gmail API `messages.send` method, with the
  reply's `threadId` set to the original `threadId` to preserve thread continuity.
- **FR-GH-007**: The handler MUST deduplicate incoming Gmail messages using the Gmail `message_id`.
  A seen `message_id` MUST be silently dropped without producing a TicketMessage.
- **FR-GH-008**: The handler MUST return HTTP 200 for all valid Pub/Sub payloads, including cases
  where no actionable messages are found (prevents Pub/Sub retry storms).
- **FR-GH-009**: Missing or invalid OAuth2 credentials MUST be caught and logged; the webhook
  MUST NOT crash or return a 5xx.

**WhatsApp Handler (`production/channels/whatsapp_handler.py`)**

- **FR-WH-001**: The handler MUST expose a POST webhook endpoint that accepts Twilio webhook
  payloads (form-encoded, containing `From`, `Body`, `MessageSid`, and optional media fields).
- **FR-WH-002**: The handler MUST validate the `X-Twilio-Signature` header using the Twilio
  `RequestValidator` class with the configured Auth Token. Requests failing validation MUST
  receive HTTP 403 and be dropped.
- **FR-WH-003**: The handler MUST extract: `From` (phone number in E.164 format), `Body`
  (message text), and `MessageSid` from the Twilio webhook payload.
- **FR-WH-004**: The handler MUST normalise each WhatsApp message into a `TicketMessage`
  with `channel="whatsapp"`, populating `id`, `customer_phone`, `message`, `received_at`,
  and `metadata["message_sid"]`.
- **FR-WH-005**: The handler MUST publish each `TicketMessage` to the Kafka topic `tickets.whatsapp`.
- **FR-WH-006**: The handler MUST send replies via the Twilio REST API `messages.create` method,
  sending from the configured NexaFlow Twilio WhatsApp number to the customer's `From` number.
- **FR-WH-007**: The handler MUST deduplicate incoming messages using `MessageSid`. A seen
  `MessageSid` MUST be silently dropped without producing a TicketMessage.
- **FR-WH-008**: WhatsApp messages with an empty `Body` or media-only messages MUST produce a
  TicketMessage with a `"[media attachment — no text]"` placeholder body; the endpoint MUST NOT
  return an error.
- **FR-WH-009**: The handler MUST return HTTP 200 for all successfully validated requests,
  including empty-body and duplicate cases.

**Shared Behaviour (Both Handlers)**

- **FR-SH-001**: Deduplication state MUST be maintained in an in-memory `set` keyed by
  `message_id` / `MessageSid`. A Redis-backed implementation is explicitly deferred to production.
- **FR-SH-002**: All errors (API failures, Kafka publish errors, parse errors) MUST be logged to
  `stderr` with context (handler name, error type, identifier).
- **FR-SH-003**: Neither handler MUST allow an unhandled exception to propagate beyond the
  webhook endpoint function. All exceptions MUST be caught and converted to appropriate HTTP
  responses (400 for client errors, 200 for internal errors that should not trigger retries).
- **FR-SH-004**: Both handlers MUST produce `TicketMessage` instances that are structurally
  identical to those produced by the prototype (`src/agent/models.py::TicketMessage`).
- **FR-SH-005**: Environment variables `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`,
  `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and `TWILIO_WHATSAPP_NUMBER` MUST be read at
  startup; missing variables MUST be logged but MUST NOT crash the process at import time
  (fail on first actual API call instead).

### Key Entities

- **TicketMessage** (`src/agent/models.py`): The unified inbound message contract shared by
  all three channels. Both handlers MUST produce instances of this exact type. Key fields:
  `id` (str UUID), `channel` (Channel enum), `customer_email` (str | None),
  `customer_phone` (str | None), `subject` (str | None), `message` (str), `received_at` (str ISO8601),
  `metadata` (dict — channel-specific extras like `thread_id`, `message_sid`).

- **Pub/Sub Notification** (Gmail only): The outer push payload from Google Cloud Pub/Sub.
  Contains `message.data` (base64url-encoded JSON with `emailAddress` and `historyId`) and
  `message.messageId` (Pub/Sub-level dedup key, distinct from Gmail `message_id`).

- **Twilio Webhook Payload** (WhatsApp only): Form-encoded POST body with `From`, `Body`,
  `MessageSid`, `NumMedia`, and optional `MediaUrl{N}` fields. The `X-Twilio-Signature` header
  is the HMAC-SHA1 security token for request validation.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of syntactically valid Gmail Pub/Sub notifications result in a HTTP 200
  response — the webhook never returns 5xx under any error condition.
- **SC-002**: 100% of Twilio webhook requests with an invalid `X-Twilio-Signature` are
  rejected with HTTP 403 — no message is processed without valid Twilio authentication.
- **SC-003**: Duplicate message suppression rate is 100% — a `message_id` / `MessageSid`
  seen twice in the same process lifetime produces exactly one TicketMessage.
- **SC-004**: Every TicketMessage produced by either handler is structurally valid against the
  `TicketMessage` schema — no missing required fields, no type mismatches.
- **SC-005**: End-to-end latency from webhook receipt to Kafka publish is under 3 seconds
  for a single message under normal API conditions (excluding the agent processing time).
- **SC-006**: The `send_response` stub in `production/agent/tools.py` is replaced with real
  dispatch — email replies use `threadId` continuity; WhatsApp replies reach the customer's
  `From` number via Twilio.
- **SC-007**: Zero test regressions — the existing 122-test suite continues to pass after
  the channel handlers are wired in.

---

## Assumptions

1. **Gmail OAuth flow is pre-completed.** Credentials (`credentials.json` / `token.json`) exist
   on disk before the handler starts. The spec does not cover the initial OAuth2 consent screen.
2. **Twilio Sandbox** is used for development/hackathon. A production Twilio WhatsApp Business
   account is out of scope.
3. **Kafka is running** (local Docker or existing production cluster). Kafka bootstrap server
   address is available via `KAFKA_BOOTSTRAP_SERVERS` env var.
4. **In-memory deduplication** is acceptable for the hackathon — restarts clear the seen-set.
   Redis-backed persistence is explicitly deferred.
5. **FastAPI is the web framework** for both webhook endpoints (already in the stack;
   `requirements.txt` has `fastapi`).
6. **`send_response` in `production/agent/tools.py`** is modified to call the channel handlers
   rather than replaced wholesale — the tool interface (`SendResponseInput`) is unchanged.
7. **Customer name** is not available in raw Gmail / WhatsApp payloads. The `customer_name`
   field in TicketMessage is populated as "Valued Customer" until the agent resolves identity
   via `get_or_create_customer`.
8. **`tickets.email` and `tickets.whatsapp` are the correct Kafka topic names** per the spec
   (`specs/customer-success-fte-spec.md` §2 and existing `fte.tickets.incoming` queue design).
   The handlers publish to channel-specific topics that a Kafka consumer bridges to the unified
   `fte.tickets.incoming` topic — OR publish directly to `fte.tickets.incoming` with channel
   field set. [NEEDS CLARIFICATION: confirm whether to publish to channel-specific topics or
   directly to the unified `fte.tickets.incoming` topic — this affects consumer routing design.]

---

## Out of Scope

- Next.js Web Support Form (Phase 4D, separate spec)
- Gmail OAuth2 initial consent screen / token refresh automation
- Twilio production WhatsApp Business account provisioning
- Redis-backed deduplication (deferred to production hardening)
- Multi-tenant Gmail watching (single support inbox only)
- Inbound media / attachment processing (images, audio, documents)
- Rate limiting on webhook endpoints
- Kafka consumer that reads from `tickets.*` topics and dispatches to the agent (Phase 4E)
