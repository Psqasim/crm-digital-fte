# Feature Specification: Phase 2E — Agent Skills Manifests

**Feature Branch**: `003-mcp-server`
**Created**: 2026-04-03
**Status**: Draft
**Phase**: 2E (Incubation — Define Agent Skills)

---

## Overview

Formalize the NexaFlow AI Customer Success agent's reusable capabilities as structured skill manifests. Each manifest is a machine-readable, technology-agnostic definition of WHEN a capability is invoked, WHAT it accepts as input, WHAT it returns as output, how it connects to existing MCP tools and Python modules, and what it must never do.

**Skills are NOT code.** They are formal behavioral contracts that the agent runtime uses to select and invoke capabilities, and that future test harnesses use to validate agent behavior.

Five skills are required by GIAIC Hackathon 5 Exercise 1.5.

---

## User Scenarios & Testing

### User Story 1 — Agent Retrieves Knowledge for a Product Question (Priority: P1)

A customer asks "How do I connect NexaFlow to Slack?" The agent recognizes this as a product question, invokes the Knowledge Retrieval Skill, and receives ranked documentation snippets it uses to compose its answer.

**Why this priority**: Every factual response depends on accurate knowledge retrieval. If this skill misfires, the agent either hallucinates or gives no answer.

**Independent Test**: Submit a known product question as skill input; verify the output contains at least one snippet with a non-zero relevance score that addresses the query.

**Acceptance Scenarios**:

1. **Given** a customer message containing a product question, **When** the Knowledge Retrieval Skill is triggered, **Then** the output contains at least one documentation snippet with a relevance score > 0.
2. **Given** a query about a topic not covered in the knowledge base, **When** the skill is triggered, **Then** the output returns an empty results list without raising an error.
3. **Given** a query exceeding 500 characters, **When** the skill is triggered, **Then** the skill truncates or handles the input and returns a valid (possibly empty) result.

---

### User Story 2 — Agent Analyzes Sentiment on Every Incoming Message (Priority: P1)

Every message that arrives — regardless of channel — is passed through the Sentiment Analysis Skill before any routing or response generation. The skill returns a score, trend label, and an escalation recommendation flag that downstream skills can act on.

**Why this priority**: Sentiment is the trigger for proactive escalation. If not evaluated on every message, deteriorating customer frustration can be missed.

**Independent Test**: Pass three consecutive negative messages for one customer; verify the third invocation returns a "deteriorating" trend label and `escalation_recommended: true`.

**Acceptance Scenarios**:

1. **Given** a single message with clearly negative language, **When** the Sentiment Analysis Skill is invoked, **Then** the output includes a sentiment score < -0.3 and a trend label.
2. **Given** three successive messages with worsening sentiment, **When** the skill is invoked on the third, **Then** the trend label is "deteriorating" and `escalation_recommended` is `true`.
3. **Given** a message with neutral or positive language, **When** the skill is invoked, **Then** `escalation_recommended` is `false` and the trend label is "stable" or "improving".

---

### User Story 3 — Agent Decides Whether to Escalate After Drafting a Response (Priority: P2)

After the agent drafts a reply, the Escalation Decision Skill evaluates the full conversation context, the current sentiment trend, and the ticket's SLA status to decide whether to send the response or route the case to a human agent instead.

**Why this priority**: Escalation is the safety valve protecting customers and brand reputation. It must fire reliably but not over-trigger on routine cases.

**Independent Test**: Submit context where an Enterprise-tier customer has sent three consecutive negative messages within a 4-hour SLA window; verify `should_escalate: true` with a specific reason string.

**Acceptance Scenarios**:

1. **Given** a deteriorating sentiment trend plus an Enterprise ticket with SLA under 30 minutes remaining, **When** the Escalation Decision Skill is invoked, **Then** `should_escalate` is `true`, a reason is provided, and urgency is "critical".
2. **Given** a Starter-tier customer with stable sentiment and an open ticket under 1 hour old, **When** the skill is invoked, **Then** `should_escalate` is `false`.
3. **Given** a message containing an explicit threat or profanity trigger word, **When** the skill is invoked, **Then** `should_escalate` is `true` regardless of sentiment trend.

---

### User Story 4 — Agent Formats Response for Target Channel Before Sending (Priority: P1)

Before dispatching any reply, the Channel Adaptation Skill takes the raw response text and the target channel identifier, applies the channel-specific formatting rules, and returns the formatted version ready for delivery.

**Why this priority**: Sending an email-formatted wall of text to WhatsApp — or an informal chat response via email — damages the brand voice and readability. This skill must gate every outbound message.

**Independent Test**: Pass a 10-sentence response with a formal greeting to the WhatsApp channel; verify the output is at most 3 sentences, has no signature block, and uses conversational language.

**Acceptance Scenarios**:

1. **Given** a response and `channel: email`, **When** the Channel Adaptation Skill is invoked, **Then** the output includes a formal greeting, paragraph structure, and a NexaFlow signature block.
2. **Given** a response and `channel: whatsapp`, **When** the skill is invoked, **Then** the output is at most 3 sentences with no signature block and uses conversational language.
3. **Given** a response and `channel: web_form`, **When** the skill is invoked, **Then** the output uses semi-formal tone with optional brief greeting but no extended signature.

---

### User Story 5 — Agent Identifies Customer on Every Incoming Message (Priority: P1)

The very first step on every inbound message is to resolve the sender's identity to a unified customer profile. The Customer Identification Skill accepts any available metadata (email address, phone number, channel) and returns a stable `customer_id`, merged cross-channel history, and a flag indicating whether this is a returning customer.

**Why this priority**: Without a resolved customer identity, every downstream skill — sentiment trend, escalation history, knowledge personalization — has no shared context to operate on.

**Independent Test**: Send two messages: one from email `a@nexaflow.com` and one from WhatsApp `+1-555-0100` where both identifiers belong to the same customer profile. Verify both invocations return the same `customer_id` and the merged history contains both interactions.

**Acceptance Scenarios**:

1. **Given** a message with a known email address, **When** the Customer Identification Skill is invoked, **Then** the output contains the matching `customer_id`, merged history, and `is_returning_customer: true`.
2. **Given** a message from an unrecognized email with no prior record, **When** the skill is invoked, **Then** a new `customer_id` is created and `is_returning_customer: false`.
3. **Given** messages from email and WhatsApp that belong to the same linked profile, **When** both are processed, **Then** both return the same `customer_id` and the merged history reflects entries from both channels.

---

### Edge Cases

- What happens when the Knowledge Retrieval Skill is invoked with an empty string query? The skill must return an empty results list, not an error.
- What happens when the Sentiment Analysis Skill is invoked with no prior conversation history? The skill must return a neutral score, "insufficient data" trend, and `escalation_recommended: false`.
- What happens when the Channel Adaptation Skill receives an unrecognized channel value? The skill must return the response unchanged with a warning flag rather than raising an error.
- What happens when the Customer Identification Skill receives metadata with neither email nor phone? The skill must return an anonymous session ID and `is_returning_customer: false`.
- What happens when the Escalation Decision Skill is invoked and the escalation MCP tool is unavailable? The skill must return `should_escalate: true` with `urgency: high` as a safe fallback, not silently swallow the failure.

---

## Skill Manifests

### Skill 1 — Knowledge Retrieval

```yaml
skill_id: knowledge_retrieval_v1
name: Knowledge Retrieval
version: "1.0"

trigger:
  condition: >
    Invoke when the customer message contains a question about NexaFlow features,
    pricing, integrations, plans, or usage. Also invoke when the agent needs
    factual product content to compose an accurate reply.
  priority: 1
  invoke_before: response_generation

inputs:
  query:
    type: string
    description: The customer's question or topic to search for in the knowledge base.
    max_length: 500
    required: true

outputs:
  results:
    type: array
    description: Ordered list of matching documentation snippets.
    items:
      section_title:
        type: string
      snippet:
        type: string
        max_length: 400
      relevance_score:
        type: float
        range: [0.0, 1.0]
  result_count:
    type: integer
  query_echo:
    type: string
    description: The query as received (for logging/debugging).

connected_tools:
  - mcp_tool: search_knowledge_base
    module: src/mcp_server.py
    function: search_kb
  - module: src/agent/knowledge_base.py
    class: KnowledgeBase
    method: search

guardrails:
  - MUST NOT invent or synthesize content not present in the knowledge base.
  - MUST NOT return results from a previous query when the current query returns empty.
  - MUST NOT expose raw file paths or internal module names in the output.
  - MUST NOT block if result count is zero — return empty array, not an error.

test_cases:
  - id: TC-KR-001
    description: Known product question
    input:
      query: "How do I connect NexaFlow to Slack?"
    expected_output:
      result_count: ">= 1"
      results[0].relevance_score: "> 0.0"
      results[0].snippet: "contains 'Slack' or 'integration'"

  - id: TC-KR-002
    description: No matching documents
    input:
      query: "What is the airspeed velocity of an unladen swallow?"
    expected_output:
      result_count: 0
      results: []

  - id: TC-KR-003
    description: Empty query string
    input:
      query: ""
    expected_output:
      result_count: 0
      results: []
```

---

### Skill 2 — Sentiment Analysis

```yaml
skill_id: sentiment_analysis_v1
name: Sentiment Analysis
version: "1.0"

trigger:
  condition: >
    Invoke on EVERY incoming customer message, immediately after Customer
    Identification resolves the customer_id. Must run before escalation
    decision and response generation.
  priority: 2
  invoke_before: escalation_decision, response_generation

inputs:
  message_text:
    type: string
    description: The full text of the incoming customer message.
    required: true
  customer_id:
    type: string
    description: Resolved customer identifier for retrieving prior sentiment history.
    required: true
  conversation_history:
    type: array
    description: Ordered list of prior messages in this conversation (oldest first).
    items:
      role: string       # "customer" | "agent"
      text: string
      timestamp: string  # ISO-8601
    required: false
    default: []

outputs:
  sentiment_score:
    type: float
    range: [-1.0, 1.0]
    description: >
      Negative values indicate frustration/anger; positive indicate satisfaction.
      Zero is neutral.
  sentiment_label:
    type: string
    enum: [positive, neutral, negative]
  trend_label:
    type: string
    enum: [improving, stable, deteriorating, insufficient_data]
    description: Derived from last 3+ interactions for this customer.
  escalation_recommended:
    type: boolean
    description: True when trend is deteriorating or score < -0.6.
  data_points_used:
    type: integer
    description: Number of prior messages used to compute the trend.

connected_tools:
  - mcp_tool: get_sentiment_trend
    module: src/mcp_server.py
    function: get_sentiment_trend_tool
  - module: src/agent/conversation_store.py
    class: ConversationStore
    method: compute_sentiment_trend
  - module: src/agent/escalation_evaluator.py
    function: evaluate_escalation

guardrails:
  - MUST NOT skip invocation even if message appears clearly positive.
  - MUST NOT store sentiment scores under a different customer_id than the resolved one.
  - MUST NOT recommend escalation solely based on one message unless score < -0.8.
  - MUST return trend_label "insufficient_data" (not an error) when fewer than 3 prior messages exist.

test_cases:
  - id: TC-SA-001
    description: Single strongly negative message, no history
    input:
      message_text: "This is completely broken and I am furious! Nothing works!"
      customer_id: "cust_001"
      conversation_history: []
    expected_output:
      sentiment_score: "< -0.5"
      trend_label: insufficient_data
      escalation_recommended: false

  - id: TC-SA-002
    description: Third consecutive negative message — trend deteriorating
    input:
      message_text: "Still not working after your last reply. Very disappointed."
      customer_id: "cust_002"
      conversation_history:
        - role: customer
          text: "I am having trouble."
          timestamp: "2026-04-03T08:00:00Z"
        - role: customer
          text: "Getting worse, nobody responding."
          timestamp: "2026-04-03T09:00:00Z"
    expected_output:
      trend_label: deteriorating
      escalation_recommended: true

  - id: TC-SA-003
    description: Positive message, stable history
    input:
      message_text: "Thank you, the integration is working perfectly now!"
      customer_id: "cust_003"
      conversation_history:
        - role: customer
          text: "Thanks for the help."
          timestamp: "2026-04-02T10:00:00Z"
    expected_output:
      sentiment_label: positive
      escalation_recommended: false
```

---

### Skill 3 — Escalation Decision

```yaml
skill_id: escalation_decision_v1
name: Escalation Decision
version: "1.0"

trigger:
  condition: >
    Invoke AFTER the agent has drafted a response but BEFORE sending it.
    Also invoke immediately if Sentiment Analysis returns
    escalation_recommended: true — in that case, skip drafting entirely.
  priority: 3
  invoke_after: sentiment_analysis
  invoke_before: channel_adaptation, send_response

inputs:
  customer_id:
    type: string
    required: true
  ticket_id:
    type: string
    required: true
  customer_plan:
    type: string
    enum: [starter, growth, enterprise]
    required: true
  ticket_age_minutes:
    type: integer
    description: Minutes elapsed since ticket was created.
    required: true
  sentiment_trend:
    type: string
    enum: [improving, stable, deteriorating, insufficient_data]
    required: true
  escalation_recommended_by_sentiment:
    type: boolean
    required: true
  message_text:
    type: string
    description: The latest customer message — checked for explicit trigger phrases.
    required: true
  previous_escalations:
    type: integer
    description: Number of prior escalations for this customer in the last 30 days.
    default: 0

outputs:
  should_escalate:
    type: boolean
  reason:
    type: string
    description: Human-readable explanation of the escalation decision.
    nullable: true
  urgency:
    type: string
    enum: [low, medium, high, critical]
    nullable: true
    description: Populated only when should_escalate is true.

connected_tools:
  - mcp_tool: escalate_to_human
    module: src/mcp_server.py
    function: escalate_tool
  - module: src/agent/escalation_evaluator.py
    function: evaluate_escalation
  - file: context/escalation-rules.md
    description: Authoritative escalation rule definitions.

guardrails:
  - MUST NOT escalate based solely on ticket age for Starter-tier customers (they have no SLA).
  - MUST escalate (should_escalate: true, urgency: critical) when message_text contains explicit threats or profanity trigger words defined in escalation-rules.md.
  - MUST NOT silently suppress escalation if the escalate_to_human MCP tool is unavailable — surface the error.
  - MUST NOT change ticket status itself — that is the responsibility of the escalate_to_human MCP tool.

escalation_rules_summary:
  enterprise_sla_minutes: 240   # 4 hours
  growth_sla_minutes: 1440      # 24 hours
  starter_sla: none
  auto_escalate_on: [threat, profanity, legal_mention, data_breach_mention]
  sentiment_escalate_threshold: deteriorating + sentiment_score < -0.6

test_cases:
  - id: TC-ED-001
    description: Enterprise ticket nearing 4-hour SLA with deteriorating sentiment
    input:
      customer_id: "cust_ent_001"
      ticket_id: "tkt_001"
      customer_plan: enterprise
      ticket_age_minutes: 210
      sentiment_trend: deteriorating
      escalation_recommended_by_sentiment: true
      message_text: "Still waiting. This is unacceptable."
      previous_escalations: 0
    expected_output:
      should_escalate: true
      urgency: critical

  - id: TC-ED-002
    description: Starter tier, stable sentiment, young ticket
    input:
      customer_id: "cust_str_001"
      ticket_id: "tkt_002"
      customer_plan: starter
      ticket_age_minutes: 45
      sentiment_trend: stable
      escalation_recommended_by_sentiment: false
      message_text: "How do I reset my password?"
      previous_escalations: 0
    expected_output:
      should_escalate: false

  - id: TC-ED-003
    description: Message with explicit threat regardless of plan/SLA
    input:
      customer_id: "cust_gr_001"
      ticket_id: "tkt_003"
      customer_plan: growth
      ticket_age_minutes: 10
      sentiment_trend: stable
      escalation_recommended_by_sentiment: false
      message_text: "I am going to report you to my lawyer and sue NexaFlow."
      previous_escalations: 0
    expected_output:
      should_escalate: true
      urgency: critical
```

---

### Skill 4 — Channel Adaptation

```yaml
skill_id: channel_adaptation_v1
name: Channel Adaptation
version: "1.0"

trigger:
  condition: >
    Invoke on EVERY outbound response, immediately before the send_response
    MCP tool is called. No response may be dispatched without passing through
    this skill first.
  priority: 4
  invoke_after: response_generation, escalation_decision
  invoke_before: send_response

inputs:
  response_text:
    type: string
    description: The raw response draft produced by the agent.
    required: true
  target_channel:
    type: string
    enum: [email, whatsapp, web_form]
    required: true
  customer_name:
    type: string
    description: Used for personalized greeting in email channel.
    required: false
    nullable: true
  agent_signature_enabled:
    type: boolean
    description: When false, suppress signature even on email channel.
    default: true

outputs:
  formatted_response:
    type: string
    description: The response text after channel-specific formatting is applied.
  channel_applied:
    type: string
    description: Echo of the target_channel value (for logging).
  formatting_notes:
    type: array
    description: List of transformations applied (e.g., "truncated to 3 sentences", "added signature").
    items:
      type: string

channel_rules:
  email:
    - Include formal greeting: "Dear [customer_name]," or "Hello [customer_name],"
    - Use full paragraphs with proper punctuation.
    - Append NexaFlow support signature block.
    - No strict length limit (but keep under 400 words).
  whatsapp:
    - Maximum 3 sentences total.
    - No greeting or signature block.
    - Conversational, friendly tone.
    - Use plain text only — no markdown headers or bullet lists.
  web_form:
    - Semi-formal tone (no "Dear", brief "Hi [name]" acceptable).
    - 2–6 sentences or a short bullet list.
    - No signature block.
    - Light markdown (bold for key steps) is acceptable.

connected_tools:
  - module: src/agent/channel_formatter.py
    functions: [format_email_response, format_whatsapp_response, format_web_form_response]
  - mcp_tool: send_response
    module: src/mcp_server.py
    function: send_response_tool
    note: send_response is invoked AFTER this skill completes, not by this skill.

guardrails:
  - MUST NOT send the unformatted response_text directly — always apply channel rules.
  - MUST NOT add a signature block to whatsapp or web_form channels.
  - MUST NOT exceed 3 sentences for whatsapp channel — truncate with "..." if necessary.
  - MUST NOT alter factual content during formatting — only structure and style may change.
  - MUST return the response unchanged (with a warning flag) for an unrecognized channel value, rather than raising an error.

test_cases:
  - id: TC-CA-001
    description: Long response formatted for WhatsApp
    input:
      response_text: >
        Thank you for reaching out to NexaFlow support. I understand you are
        experiencing difficulty connecting your workflow to Slack. First, please
        navigate to the Integrations section in your dashboard. Then select Slack
        from the list and follow the OAuth authorization steps. Once authorized,
        your workflow triggers will appear in the Slack channel you selected.
        Please let us know if you need further help. We are here for you.
      target_channel: whatsapp
      customer_name: "Ali"
    expected_output:
      formatted_response: "contains <= 3 sentences"
      formatting_notes: "contains 'truncated to 3 sentences'"

  - id: TC-CA-002
    description: Response formatted for email with signature
    input:
      response_text: "The integration steps are as follows: go to Settings > Integrations."
      target_channel: email
      customer_name: "Sara"
      agent_signature_enabled: true
    expected_output:
      formatted_response: "starts with 'Dear Sara' or 'Hello Sara'"
      formatted_response: "ends with NexaFlow signature block"

  - id: TC-CA-003
    description: Unknown channel — passthrough with warning
    input:
      response_text: "Here is your answer."
      target_channel: sms
    expected_output:
      formatted_response: "Here is your answer."
      formatting_notes: "contains 'unrecognized channel'"
```

---

### Skill 5 — Customer Identification

```yaml
skill_id: customer_identification_v1
name: Customer Identification
version: "1.0"

trigger:
  condition: >
    Invoke as the FIRST step on every incoming message, before any other skill.
    No downstream skill may run until a customer_id is resolved.
  priority: 0
  invoke_before: sentiment_analysis, knowledge_retrieval, escalation_decision

inputs:
  channel:
    type: string
    enum: [email, whatsapp, web_form]
    required: true
  email:
    type: string
    format: email
    required: false
    nullable: true
    description: Present for email and web_form channels.
  phone:
    type: string
    required: false
    nullable: true
    description: Present for whatsapp channel. E.164 format preferred.
  display_name:
    type: string
    required: false
    nullable: true
    description: Name as provided in the incoming message metadata.
  raw_message_id:
    type: string
    required: true
    description: Channel-specific message identifier (for idempotency).

outputs:
  customer_id:
    type: string
    description: Stable, unified identifier for this customer across all channels.
  is_returning_customer:
    type: boolean
  customer_plan:
    type: string
    enum: [starter, growth, enterprise, unknown]
  merged_history_summary:
    type: object
    description: Lightweight summary of prior interactions (not full history).
    properties:
      total_tickets: integer
      open_tickets: integer
      last_channel: string
      last_interaction_timestamp: string  # ISO-8601 or null
  resolution_action:
    type: string
    enum: [matched_existing, created_new, matched_by_cross_channel_link]
    description: How the customer_id was resolved.

connected_tools:
  - module: src/agent/conversation_store.py
    class: ConversationStore
    method: resolve_identity
  - module: src/agent/models.py
    class: CustomerProfile

guardrails:
  - MUST NOT proceed without resolving at least a temporary customer_id — even for anonymous sessions.
  - MUST NOT merge two customer profiles without at least one shared identifier (email or phone).
  - MUST NOT expose PII (raw email or phone) in the output — output only customer_id.
  - MUST create a new profile (is_returning_customer: false) rather than failing when no match is found.
  - MUST be idempotent — calling with the same raw_message_id twice must return the same customer_id.

test_cases:
  - id: TC-CI-001
    description: Known customer by email
    input:
      channel: email
      email: "sara.malik@company.com"
      phone: null
      display_name: "Sara Malik"
      raw_message_id: "msg_email_001"
    expected_output:
      customer_id: "cust_xyz"  # existing profile
      is_returning_customer: true
      resolution_action: matched_existing

  - id: TC-CI-002
    description: New customer — no prior record
    input:
      channel: web_form
      email: "newuser@startup.io"
      phone: null
      display_name: "New User"
      raw_message_id: "msg_web_002"
    expected_output:
      is_returning_customer: false
      resolution_action: created_new

  - id: TC-CI-003
    description: Cross-channel link — same customer, WhatsApp + email
    input:
      channel: whatsapp
      email: null
      phone: "+923001234567"
      display_name: null
      raw_message_id: "msg_wa_003"
    expected_output:
      customer_id: "cust_xyz"  # same as TC-CI-001 (phone linked to Sara's profile)
      is_returning_customer: true
      resolution_action: matched_by_cross_channel_link
```

---

## Agent Invocation Order

The skills MUST be invoked in the following order on every incoming message:

```
[INBOUND MESSAGE]
       │
       ▼
1. Customer Identification  (priority 0 — always first)
       │
       ▼
2. Sentiment Analysis       (priority 1 — every message, uses customer_id)
       │
       ▼
3. Knowledge Retrieval      (priority 2 — only if product question detected)
       │
       ▼
4. [Response Generation]    (agent drafts reply using KB results)
       │
       ▼
5. Escalation Decision      (priority 3 — evaluate before sending)
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

## Requirements

### Functional Requirements

- **FR-001**: All 5 skill manifests MUST be defined with `skill_id`, `name`, `version`, `trigger`, `inputs`, `outputs`, `connected_tools`, `guardrails`, and `test_cases` sections.
- **FR-002**: The Customer Identification Skill MUST run as the first step on every inbound message; no other skill may execute before it resolves a `customer_id`.
- **FR-003**: The Sentiment Analysis Skill MUST run on every inbound message (P1), not only when negative sentiment is suspected.
- **FR-004**: The Channel Adaptation Skill MUST gate every outbound response — no reply may be sent without passing through it.
- **FR-005**: The Escalation Decision Skill MUST evaluate after response drafting but before channel adaptation and sending.
- **FR-006**: The Knowledge Retrieval Skill MUST return results without error when the query matches nothing — empty results, not an exception.
- **FR-007**: Each skill MUST define at least one guardrail that explicitly states what the skill MUST NOT do.
- **FR-008**: Each skill manifest MUST include 2–3 test cases with concrete example inputs and expected output criteria.
- **FR-009**: The Channel Adaptation Skill MUST enforce email=formal+signature, whatsapp=max-3-sentences, web_form=semi-formal with no signature.
- **FR-010**: The Escalation Decision Skill MUST auto-escalate with urgency "critical" when the message contains explicit threat/legal/profanity trigger phrases as defined in `context/escalation-rules.md`.
- **FR-011**: All skill inputs and outputs MUST be serialisable (JSON-compatible types) to enable future MCP tool wrapping.
- **FR-012**: Skills MUST delegate actual execution to existing modules (`src/agent/`) and MCP tools — they MUST NOT reimplement business logic.

### Key Entities

- **Skill Manifest**: The formal definition of a capability — contains trigger, I/O schema, connected tools, guardrails, and test cases.
- **Trigger**: The condition and ordering constraint that determines when a skill is invoked.
- **Guardrail**: A constraint that defines what a skill is explicitly prohibited from doing.
- **Test Case**: A concrete input/expected-output pair used to validate skill behavior.
- **Invocation Order**: The mandatory sequence in which skills are called for each inbound message.

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: All 5 skill manifests are complete — no unresolved placeholders, every mandatory section present.
- **SC-002**: The invocation order diagram is unambiguous and consistent with GIAIC Hackathon 5 Exercise 1.5 requirements.
- **SC-003**: Each skill manifest includes at least 2 test cases with concrete input values and verifiable expected outputs.
- **SC-004**: Every skill's `connected_tools` list references only modules and MCP tools that exist in the current codebase (`specs/003-mcp-server/` and `src/agent/`).
- **SC-005**: The Channel Adaptation Skill's formatting rules are quantitatively testable (e.g., "max 3 sentences" is verifiable).
- **SC-006**: The Escalation Decision Skill's escalation rules are traceable to `context/escalation-rules.md`.
- **SC-007**: All 5 skill manifests are consumable as a structured reference by `/sp.plan` without requiring additional clarification.

---

## Assumptions

- `ConversationStore.resolve_identity()` exists or will be added to `src/agent/conversation_store.py` as a first task in Phase 2E implementation.
- The sentiment scoring logic already available in `compute_sentiment_trend` (Phase 2C) is the source of truth for sentiment scores used by the Sentiment Analysis Skill.
- The `escalation-rules.md` context file is the authoritative source for trigger phrases and SLA thresholds referenced by the Escalation Decision Skill.
- Skill manifests in this document are YAML-formatted for readability but will be machine-parsed during future implementation phases.
- "Max 3 sentences" for WhatsApp is enforced by `channel_formatter.py` — the Channel Adaptation Skill invokes that module rather than re-implementing truncation.

---

## Out of Scope

- Code implementation of skills — manifests only (Phase 2F will implement).
- Skill versioning and hot-reload mechanisms.
- Skill composition chains beyond the defined invocation order.
- Skill-level observability/metrics collection (deferred to Phase 3).
- Any new MCP tools beyond those already defined in Phase 2D.

---

## Dependencies

- Phase 2B deliverable: `src/agent/knowledge_base.py`, `src/agent/channel_formatter.py`
- Phase 2C deliverable: `src/agent/conversation_store.py` (ConversationStore, compute_sentiment_trend), `src/agent/escalation_evaluator.py`
- Phase 2D deliverable: `src/mcp_server.py` (all 7 MCP tools)
- Context files: `context/escalation-rules.md` (trigger phrases, SLA thresholds)
- MCP tools referenced: `search_knowledge_base`, `get_sentiment_trend`, `escalate_to_human`, `send_response`
