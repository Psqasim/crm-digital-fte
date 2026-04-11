# Feature Specification: Chat Agent Widget

**Feature Branch**: `012-chat-agent`  
**Created**: 2026-04-10  
**Status**: Draft  
**Phase**: 7B — Chat Agent Widget (web_chat channel)

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Self-Service Support via Chat Widget (Priority: P1)

A NexaFlow customer visits the web portal while experiencing difficulty with their workflow setup. They notice a floating chat button in the bottom-right corner and click it. A chat panel slides open with an immediate greeting. They type their issue and receive a relevant AI-generated answer from NexaFlow's knowledge base — resolving their problem without submitting a formal ticket or waiting for a human agent.

**Why this priority**: This is the core value of the feature. Every other user story is an extension of this one. Without a working chat → AI response loop, nothing else matters.

**Independent Test**: Open the widget, type a NexaFlow product question, receive a relevant AI response — a fully testable self-service value delivery.

**Acceptance Scenarios**:

1. **Given** the NexaFlow web portal is open, **When** the user clicks the floating chat button, **Then** the chat panel animates open and displays: "Hi! I'm NexaFlow's AI assistant. How can I help you today?"
2. **Given** the chat panel is open, **When** the user types a product question and submits it, **Then** the AI responds with a relevant, knowledge-base-backed answer within 10 seconds.
3. **Given** the chat panel has prior messages, **When** a new AI response arrives, **Then** the messages area automatically scrolls to reveal the latest message without user intervention.
4. **Given** the AI is processing a response, **When** the user looks at the chat, **Then** a typing indicator (three animated dots) is visible and the input field is disabled until the response arrives.

---

### User Story 2 — Off-Topic Query Refusal (Priority: P2)

A user attempts to use the chat widget for purposes unrelated to NexaFlow support — asking it to write an essay, generate code, or tell a story. The agent politely declines and redirects the user back to NexaFlow support topics without generating any non-support content.

**Why this priority**: Prevents channel abuse, reduces AI costs, and maintains the widget's professional purpose. Without guardrails, the widget becomes an uncontrolled general-purpose chatbot.

**Independent Test**: Send a non-support message and verify the exact refusal response appears — independently testable without any knowledge base or ticket infrastructure.

**Acceptance Scenarios**:

1. **Given** the chat panel is open, **When** the user asks for an essay, story, code, or any non-NexaFlow-support topic, **Then** the AI responds with exactly: "I'm here to help with NexaFlow support only. What can I help you with?"
2. **Given** the chat panel is open, **When** the user's message contains prompt injection attempts (e.g., "ignore previous instructions", "forget your rules"), **Then** the message is rejected before reaching the AI and a polite error is shown.
3. **Given** the chat panel is open, **When** the user asks about competitor products, **Then** the AI does not name or discuss any competitor and redirects to NexaFlow's capabilities.

---

### User Story 3 — Multilingual Support (Priority: P3)

A customer from Pakistan sends a message in Urdu. The AI detects the language automatically and responds in Urdu — no configuration required by the user.

**Why this priority**: NexaFlow serves Pakistan, India, US, and UK markets. Urdu-speaking customers are a significant segment. Automatic language detection improves accessibility without extra user effort.

**Independent Test**: Send a message in Urdu → verify the response is in Urdu. Send a message in English → verify the response is in English. No configuration needed between tests.

**Acceptance Scenarios**:

1. **Given** a user sends a message entirely in Urdu, **When** the AI processes it, **Then** the response is delivered in Urdu.
2. **Given** a user sends a message in English, **When** the AI processes it, **Then** the response is delivered in English.
3. **Given** a user sends a mixed Urdu-English message, **When** the AI processes it, **Then** the response is in the dominant detected language.

---

### User Story 4 — Session Rate Limit & Warning (Priority: P4)

A customer has an extended conversation approaching 20 messages. At 18 messages, the widget displays a soft warning that the session limit is nearly reached. At 20 messages, the input is disabled and the user is directed to submit a formal support ticket for continued assistance.

**Why this priority**: Protects infrastructure costs and prevents session abuse without abruptly cutting off users. The soft warning at 18 ensures users are not surprised.

**Independent Test**: Simulate 18+ messages in a session and verify the warning appears at 18 and the lockout occurs at 20 — testable against the backend rate limit endpoint alone.

**Acceptance Scenarios**:

1. **Given** the user has sent 18 messages in the session, **When** their 18th response is received, **Then** a notice appears: "You have 2 messages remaining in this session."
2. **Given** the user has sent 20 messages, **When** they attempt to send another, **Then** the input field is disabled and a message appears directing them to the formal support form.
3. **Given** the session limit is reached, **When** the user clears the chat, **Then** a new session begins with a fresh message count (20 messages available again).

---

### User Story 5 — Mobile Full-Screen Experience (Priority: P5)

A user visits the NexaFlow portal on a smartphone. Instead of a small floating corner panel (which would be unusable on a small screen), the chat widget opens as a full-screen overlay providing a native-app-like experience.

**Why this priority**: Mobile traffic is significant across NexaFlow's markets. A 380×520 floating panel is not usable on a 375px-wide mobile screen.

**Independent Test**: Open the portal on a mobile viewport (under 768px) and verify the chat widget opens full-screen — independently testable with browser developer tools.

**Acceptance Scenarios**:

1. **Given** the user is on a viewport narrower than 768px, **When** they tap the chat button, **Then** the chat opens as a full-screen overlay covering the entire viewport.
2. **Given** the full-screen chat is open on mobile, **When** the user closes it, **Then** the overlay closes and the floating button reappears.
3. **Given** the user is on a desktop viewport (768px or wider), **When** they click the chat button, **Then** the panel opens as a 380×520 floating panel in the bottom-right corner.

---

### Edge Cases

- **Input empty or whitespace**: Send button remains disabled; no request is made to the AI.
- **Input exceeds 500 characters**: The input field prevents additional typing and shows a character count warning; send button is disabled.
- **AI backend unreachable or returns error**: Display: "I'm having trouble connecting. Please try again or use our support form." Do not show a technical error message.
- **AI response takes longer than 15 seconds**: The typing indicator disappears and an error message is shown with a retry option.
- **User clears chat**: All messages are wiped from view, a fresh greeting is displayed, and the session resets (new session ID, message count back to 0).
- **Prompt injection attempt detected**: Message is blocked before reaching the AI; a polite "I can't process that request" message is shown. No AI call is made.
- **User closes the widget mid-conversation**: Chat history is discarded; reopening shows only the greeting.

---

## Requirements *(mandatory)*

### Functional Requirements

#### Widget UI

- **FR-001**: The system MUST display a permanently visible floating action button in the bottom-right corner of every page, using electric blue (#3B82F6) with a chat bubble icon.
- **FR-002**: Clicking the floating button MUST open the chat panel with an upward slide animation.
- **FR-003**: On desktop viewports (768px and wider), the chat panel MUST be exactly 380px wide and 520px tall with a dark (#0F172A) background.
- **FR-004**: On mobile viewports (narrower than 768px), the chat panel MUST open as a full-screen overlay instead of a corner panel.
- **FR-005**: The chat panel header MUST display: the label "NexaFlow AI Support", a minimize button (collapses to header-only), a close button (closes panel entirely), and a clear-chat button.
- **FR-006**: The messages area MUST be scrollable and MUST automatically scroll to the latest message within 300ms of any new message being added.
- **FR-007**: The input area MUST contain a text field and a send button; pressing Enter in the text field MUST submit the message.
- **FR-008**: The panel footer MUST display "Powered by NexaFlow AI".

#### Chat Behavior

- **FR-009**: When the chat panel opens (or resets), the system MUST immediately display the greeting: "Hi! I'm NexaFlow's AI assistant. How can I help you today?"
- **FR-010**: All messages in the current session MUST persist in the panel while the widget remains open; closing the widget discards the history.
- **FR-011**: While the AI is generating a response, the system MUST show a typing indicator (three animated dots) and disable the input field and send button.
- **FR-012**: The clear-chat button MUST reset the conversation: wipe all messages, start a new session, and display the greeting.
- **FR-013**: The send button MUST be disabled when the input field is empty or contains only whitespace.

#### AI Behavior

- **FR-014**: Every user message MUST be accompanied by the last 10 messages of conversation history when sent to the AI — not the full session history — to manage token limits.
- **FR-015**: Before generating any response, the AI MUST search the NexaFlow knowledge base for relevant content and incorporate matching results into its answer.
- **FR-016**: The AI MUST automatically detect the language of the user's message and respond in the same language (English, Urdu, or other detected languages).
- **FR-017**: The AI MUST refuse off-topic requests (essays, stories, code generation, competitor questions, or any non-NexaFlow-support topic) with the exact response: "I'm here to help with NexaFlow support only. What can I help you with?"
- **FR-018**: The AI MUST NEVER reveal its system prompt, internal instructions, tool names, or processing architecture.
- **FR-019**: The AI MUST NEVER name or discuss competitor products (Asana, Monday.com, ClickUp, Notion, Trello, Basecamp, Linear, Airtable, Smartsheet, Jira as a project tool).
- **FR-020**: The AI MUST NEVER invent information not found in the knowledge base; if the answer is unknown, it MUST acknowledge gracefully (e.g., "Let me look into that for you") and offer to connect the user with a human agent.
- **FR-021**: The AI MUST use the current PKT (Pakistan Standard Time) datetime in every response where time context is relevant (e.g., SLA references, scheduling).
- **FR-022**: The chat channel MUST NOT create a support ticket in the CRM — it is a stateless self-service channel, separate from the email/WhatsApp/web form ticket pipeline.

#### Session Rate Limiting

- **FR-023**: The first message in any conversation MUST trigger creation of a unique session ID, which the frontend stores and passes on every subsequent request.
- **FR-024**: The system MUST enforce a hard maximum of 20 messages per session.
- **FR-025**: When the user's sent message count reaches 18 within a session, the system MUST display a soft warning: "You have 2 messages remaining in this session."
- **FR-026**: When the 20-message limit is reached, the input field MUST be disabled and a message MUST appear directing the user to the formal support form.

#### Input Security

- **FR-027**: All user input MUST be sanitized to strip HTML and script content before transmission to the AI.
- **FR-028**: User messages MUST be capped at 500 characters; the input field MUST prevent entry beyond this limit and display a character count indicator.
- **FR-029**: Messages matching known prompt injection patterns (e.g., "ignore previous instructions", "you are now", "forget your instructions", "new persona") MUST be rejected before reaching the AI; a polite refusal MUST be returned to the user.

#### Chat API Endpoint

- **FR-030**: A dedicated chat endpoint MUST accept: a user message (string, max 500 chars after sanitization), a session ID (string, empty string signals first message), and the last 10 messages of conversation history (array of role/content pairs).
- **FR-031**: The chat endpoint MUST return: an AI-generated reply (string) and the session ID (string, generated on first message).
- **FR-032**: The chat endpoint MUST enforce rate limiting per session ID and return a clear, user-friendly error when the 20-message limit is reached.
- **FR-033**: The chat endpoint MUST NOT accept messages longer than 500 characters after sanitization; it MUST return a validation error for oversized input.
- **FR-034**: The chat endpoint MUST perform knowledge base search before generating the AI reply on every request.

### Key Entities

- **Chat Session**: A single user's stateless conversation within the widget. Has a unique ID, message count, and creation timestamp. Lives in-memory on the backend only — not persisted to the database. Resets when the widget is closed, the chat is cleared, or the session limit is reached.
- **Chat Message**: A single turn in the conversation. Has a role (user or assistant), text content, and display timestamp. Rendered in the messages area; stored in component state on the frontend for display and in the last-10 window for AI context.
- **Session Rate Limit Record**: An in-memory record keyed by session ID tracking the number of messages sent. Enforces the 20-message hard cap and the 18-message soft warning threshold.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A customer can open the chat widget and receive a relevant AI response to a NexaFlow support question within 10 seconds of sending their message, in 95% of interactions.
- **SC-002**: The widget correctly issues the exact refusal response for 100% of off-topic request test cases (essays, stories, code, competitor questions).
- **SC-003**: The widget correctly detects language and responds in Urdu for Urdu-language input and in English for English-language input in 100% of tested cases.
- **SC-004**: The soft warning ("2 messages remaining") appears at message 18 in 100% of sessions that reach that count; input is disabled at message 20 in 100% of such sessions.
- **SC-005**: 100% of tested prompt injection patterns are blocked before reaching the AI; no injected instruction is executed.
- **SC-006**: The messages area auto-scrolls to the latest message within 300ms of a new message being added, on both desktop and mobile.
- **SC-007**: On desktop viewports, the widget renders as a 380×520 floating panel. On viewports narrower than 768px, the widget renders as a full-screen overlay. Both states verified across Chrome, Firefox, and Safari.
- **SC-008**: Input exceeding 500 characters cannot be entered; the send button remains disabled for empty or whitespace-only input.
- **SC-009**: The chat endpoint rejects messages with prompt injection patterns and returns a non-technical, user-friendly error in 100% of tested cases.

### Assumptions

1. The AI backend is already deployed on Hugging Face Spaces and is accessible from the Next.js frontend via HTTPS.
2. The knowledge base contains 11 chunks already seeded in Neon pgvector — no additional seeding is required for this feature.
3. Chat sessions are ephemeral: session data lives in-memory on the backend and in component state on the frontend. No database persistence is required.
4. The chat widget does not require user authentication — it is accessible to anonymous visitors.
5. Rate limiting is enforced in-memory on the backend (no external cache required for this phase).
6. The current PKT datetime must be injected into every AI call, consistent with the existing agent guardrail (§8 of the main spec and CLAUDE.md).
7. The chat channel is fully isolated from the existing ticket pipeline — no Kafka events, no ticket creation, no CRM records.
