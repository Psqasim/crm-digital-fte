# Feature Specification: Agent Memory and State

**Feature Branch**: `002-memory-state`  
**Created**: 2026-04-02  
**Status**: Draft  
**Phase**: 2C — Add Memory and State

---

## Overview

Extend the NexaFlow AI support agent from a stateless, single-message handler into a stateful conversational system. The agent must remember who it is talking to, what has been discussed, and how the customer's emotional state has evolved — so that every follow-up message receives context-aware, personalised responses rather than being treated as a brand-new ticket.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Multi-Turn Conversation (Priority: P1)

A customer sends an initial support message and then follows up with additional questions or clarifications within the same support session. The agent must respond as if it has read the entire conversation so far, without asking the customer to repeat themselves.

**Why this priority**: The most immediate pain point from Phase 2B. Without conversation memory, every follow-up is treated as a new ticket, forcing customers to re-explain their problem. This is the foundational capability everything else builds on.

**Independent Test**: Send two related messages from the same customer and verify the second response references or accounts for the first message's content.

**Acceptance Scenarios**:

1. **Given** a customer has already described a billing issue, **When** they send a follow-up saying "still not resolved", **Then** the agent responds with context about the original billing issue rather than asking them to describe the problem again.
2. **Given** a multi-turn conversation with 5 messages, **When** the 6th message arrives, **Then** the agent has access to all 5 prior messages and produces a coherent continuation.
3. **Given** two different customers with separate sessions, **When** each sends a follow-up, **Then** their conversation histories do not mix.

---

### User Story 2 — Cross-Channel Identity Recognition (Priority: P2)

A customer who previously contacted support via email then sends a WhatsApp message about the same issue. The agent must recognise this as the same customer and continue the conversation without starting from scratch.

**Why this priority**: NexaFlow customers use multiple channels. Without identity merging, the same customer appears as two strangers and receives duplicate, conflicting responses.

**Independent Test**: Simulate one customer contacting first via email (with known email address) and then via WhatsApp (with a phone number linked to that email). Verify the agent sees the full combined history.

**Acceptance Scenarios**:

1. **Given** a customer with email `alice@example.com` has an open ticket, **When** they message via WhatsApp from a number previously linked to that email, **Then** the agent greets them by recognition and references their existing open issue.
2. **Given** a phone number with no known email association, **When** the customer provides their email in the conversation, **Then** the system links the phone number to that email and merges any prior history.
3. **Given** two different customers using different channels with no shared identity signals, **When** both contact support, **Then** their sessions remain separate.

---

### User Story 3 — Sentiment Trend Awareness (Priority: P3)

As a conversation progresses, the agent detects whether the customer is growing more frustrated or calming down, and adjusts its tone and escalation behaviour accordingly — rather than evaluating each message in isolation.

**Why this priority**: A single frustrated message may be a momentary spike, but consistent deterioration over multiple messages is a reliable escalation signal. Trend-based detection reduces both false positives and missed escalations.

**Independent Test**: Send a sequence of messages that progressively express more frustration. Verify that escalation is triggered by the trend, not a single message, and that a recovery sequence cancels the escalation signal.

**Acceptance Scenarios**:

1. **Given** a customer whose last three messages have each been more negative than the previous, **When** the next message arrives, **Then** the agent flags this customer for priority handling even if the latest message alone is only mildly negative.
2. **Given** a customer who was frustrated but then indicates the issue is resolved, **When** the next message arrives, **Then** the sentiment trend resets and the customer is no longer flagged for escalation.
3. **Given** a single very negative message with no prior history, **When** the agent responds, **Then** it responds empathetically but does not treat this as a confirmed trend-based escalation.

---

### User Story 4 — Resolution Status Tracking (Priority: P3)

Each ticket has a lifecycle: it can be open, pending agent action, escalated to a human, or resolved. The agent tracks this status and uses it to shape its responses and avoid re-opening closed matters unnecessarily.

**Why this priority**: Without status tracking, the agent may keep offering solutions for problems the customer already confirmed are resolved, or miss that an issue needs human follow-up.

**Independent Test**: Resolve a ticket (customer confirms fix), then have the same customer send a new, unrelated question. Verify the new message opens a fresh ticket rather than re-opening the resolved one.

**Acceptance Scenarios**:

1. **Given** a ticket has been marked resolved, **When** the customer sends a follow-up confirming everything is fine, **Then** the agent acknowledges closure and does not reopen the ticket.
2. **Given** a ticket is escalated to a human agent, **When** the customer sends another message, **Then** the AI response acknowledges that a human is handling the case and does not attempt to resolve it independently.
3. **Given** a resolved ticket, **When** the customer sends a completely new question, **Then** a new ticket is opened with a fresh status rather than re-using the old ticket.

---

### User Story 5 — Topic History and Repeat Issue Detection (Priority: P4)

The agent tracks what subjects each customer has raised in past sessions so it can recognise recurring problems and tailor its response (e.g., skip basic troubleshooting steps already attempted, flag repeat issues for the product team).

**Why this priority**: Repeat issue detection improves agent efficiency and highlights product gaps, but requires multi-session memory beyond just the current conversation.

**Independent Test**: Have a customer ask about the same topic in two separate sessions. Verify the second session response acknowledges the prior contact and skips already-tried steps.

**Acceptance Scenarios**:

1. **Given** a customer previously contacted support about "workflow triggers not firing", **When** they ask about the same topic in a new session, **Then** the agent acknowledges the prior contact and does not suggest steps already attempted.
2. **Given** a customer who has contacted support more than three times about the same topic, **When** they contact again, **Then** the agent flags this as a repeat issue deserving escalation or proactive outreach.
3. **Given** a customer asking about a new topic they have not raised before, **When** the agent responds, **Then** it responds without reference to unrelated past topics.

---

### Edge Cases

- What happens when a customer's email cannot be determined from any channel? (Phone-only customer with no email provided — must function with a transient identifier.)
- What happens if two different customers share a phone number (e.g., shared office WhatsApp line)?
- What is the maximum number of messages retained per conversation before older messages are dropped?
- How is sentiment trend calculated when a message contains both positive and negative signals?
- What happens if a ticket status transition is attempted in an invalid direction (e.g., moving from `resolved` back to `open`)?

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST store and retrieve the full message history for each active conversation, keyed by a stable customer identifier.
- **FR-002**: The system MUST use email address as the primary customer identifier; all channels must resolve to this key when possible.
- **FR-003**: The system MUST resolve a phone number to an email address when a known mapping exists, or when the customer explicitly provides their email during a session.
- **FR-004**: The system MUST attach each inbound message to the correct customer's history regardless of which channel it arrives on.
- **FR-005**: The system MUST compute a sentiment trend across the last N messages (not just the current message) and expose this trend to the response and escalation logic.
- **FR-006**: The system MUST track ticket resolution status with at least four states: `open`, `pending`, `escalated`, `resolved`.
- **FR-007**: The system MUST prevent a resolved ticket from being re-opened by a follow-up confirmation; a genuinely new question from the same customer MUST open a new ticket.
- **FR-008**: The system MUST record which topics a customer has raised, keyed by topic label, and persist this across sessions (within the same process lifetime).
- **FR-009**: The system MUST make a customer's topic history available to the agent when composing a response so it can skip already-attempted steps.
- **FR-010**: The system MUST detect when an existing customer contacts via a new channel and surface their existing open ticket and full history.
- **FR-011**: The system MUST NOT expose one customer's conversation history or identity data to another customer's session under any condition.
- **FR-012**: All state for this phase MUST be held in memory only. Persistence to any external store is explicitly deferred. State is reset on process restart.

### Key Entities

- **Customer Profile**: Represents a unique individual. Holds primary email, known phone numbers (for cross-channel resolution), a list of channels used, and a catalogue of topics raised across all sessions.
- **Conversation**: A single support session for a customer. Contains an ordered list of messages, a computed sentiment trend, the current ticket status, and the channel context (which channel the session started on).
- **Message**: One turn in a conversation. Holds the text, the channel it arrived on, a timestamp, the direction (inbound from customer / outbound from agent), and a per-message sentiment score.
- **Ticket**: A support case associated with a conversation. Has a status (`open`, `pending`, `escalated`, `resolved`) and a list of topic labels discussed.
- **Sentiment Trend**: A derived signal computed from the sequence of per-message sentiment scores. Expressed as a directional label: `improving`, `stable`, or `deteriorating`.
- **Channel Identity Map**: A cross-reference table linking phone numbers and session tokens to their known email address for identity resolution.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A customer sending a follow-up message within the same session receives a response that explicitly accounts for prior context in at least 90% of manual review cases.
- **SC-002**: A customer who contacts via a second channel, where a phone-to-email mapping is known, is correctly identified and served their existing history in 100% of test cases.
- **SC-003**: Sentiment trend correctly identifies a deteriorating 3-message sequence and triggers the escalation signal in 100% of constructed test cases.
- **SC-004**: Ticket status transitions (`open` → `resolved`, `open` → `escalated`) are reflected in the very next agent response without additional prompting, in 100% of test cases.
- **SC-005**: A customer with a prior topic history receives a response that acknowledges prior contact and skips already-attempted steps in at least 80% of constructed test cases.
- **SC-006**: No cross-customer data leakage occurs in any test case (hard requirement — zero tolerance).
- **SC-007**: All 16 existing Phase 2B tests continue to pass after Phase 2C changes are introduced (no regression).

---

## Assumptions

- **A-001**: Email address is always available for email-channel contacts; it is intrinsic to the channel.
- **A-002**: Phone number is the identifier for WhatsApp contacts. Phone-to-email resolution occurs only when the customer explicitly provides their email or a prior mapping already exists in memory.
- **A-003**: The sentiment evaluation capability from Phase 2B produces a numeric score per individual message. Sentiment trend is derived by aggregating these per-message scores across the last N messages (suggested N = 3).
- **A-004**: Topic labels are the categories already produced by the Phase 2B knowledge base or escalation evaluator. No new topic taxonomy is introduced in this phase.
- **A-005**: Conversation history is capped at the last 20 messages per conversation to avoid unbounded memory growth. Messages older than the cap are dropped (not summarised) for this phase.
- **A-006**: The web form channel provides a session token as identifier; email is optional. Without email, the session token is a transient identifier that cannot be merged cross-channel.

---

## Out of Scope

- Persistent storage of any kind (database, file, cache) — deferred to Phase 4A.
- Verification or authentication of customer identity claims.
- Proactive outreach based on history (e.g., automatic follow-up messages).
- Summarisation of long conversation histories beyond the message cap.
- Admin tooling to view or manage customer state.
- GDPR and data-retention policy enforcement — memory is ephemeral for this phase.
- Multi-agent coordination (a separate agent picking up a human-escalated ticket).

---

## Dependencies

- Phase 2B modules (`models.py`, `escalation_evaluator.py`, `channel_formatter.py`, `knowledge_base.py`, `prototype.py`) must remain intact and all 16 tests must continue passing.
- The sentiment scoring capability from Phase 2B escalation evaluator provides the per-message sentiment input to the trend aggregator.
