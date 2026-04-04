# Feature Specification: Phase 2A — Incubation Exploration

**Feature Branch**: `001-incubation-exploration`
**Created**: 2026-04-01
**Status**: Complete
**Phase**: 2A — Incubation, Exercise 1.1: Initial Exploration (Hackathon Hours 1–3)

## User Scenarios & Testing

### User Story 1 — Ticket Pattern Discovery (Priority: P1)

As a developer building the FTE agent, I need to understand how customer messages
differ across the three channels (email, WhatsApp, web form) so that I can design
appropriate message normalization, response formatting, and escalation logic.

**Why this priority**: Without understanding channel-specific patterns — tone, length,
structure, identifier type — the agent cannot produce channel-appropriate responses.
This is the foundational discovery that drives all subsequent design decisions.

**Independent Test**: Run `src/agent/analyze_tickets.py` against
`context/sample-tickets.json` and verify it produces a per-channel breakdown including
average message length, category distribution, sentiment distribution, and identifier
presence. Output must contain no placeholder values.

**Acceptance Scenarios**:

1. **Given** 60 sample tickets in `context/sample-tickets.json`,
   **When** the analysis script is executed,
   **Then** it prints per-channel stats showing WhatsApp avg 14.7 words,
   email avg 49.5 words, web form avg 74.0 words.

2. **Given** the analysis output,
   **When** channel identifier coverage is checked,
   **Then** email and web form show 0% phone coverage;
   WhatsApp shows 100% phone coverage and 100% email coverage.

3. **Given** the analysis output,
   **When** category distribution is reviewed,
   **Then** `feature_question` is the top category for both email (6/20)
   and WhatsApp (9/20); web form has the highest escalation rate (4/20 = 20%).

---

### User Story 2 — Cross-Channel Customer Identification (Priority: P1)

As a developer, I need to identify which customers contacted NexaFlow support via more
than one channel so I can confirm the cross-channel continuity requirement and understand
what data makes unification possible.

**Why this priority**: Cross-channel continuity is worth 10 points in the scoring rubric
and is one of the core system guarantees. Identifying real examples from the dataset
validates the email-as-primary-key assumption.

**Independent Test**: The analysis script identifies customers with the same email address
appearing in tickets from different channels. At least 2 such customers must be found in
the 60-ticket dataset. Each cross-channel customer must have their unified ticket IDs printed.

**Acceptance Scenarios**:

1. **Given** 60 sample tickets,
   **When** cross-channel customer analysis runs,
   **Then** exactly 2 customers are identified: James Okonkwo (email + web_form,
   TKT-002 + TKT-052) and Marcus Thompson (whatsapp + web_form, TKT-025 + TKT-050).

2. **Given** Marcus Thompson's records,
   **When** TKT-050 is processed,
   **Then** TKT-025 context is surfaced showing the previous reconnect-fix attempt,
   and the agent does not repeat the same fix.

---

### User Story 3 — Edge Case Catalogue (Priority: P1)

As a developer, I need a complete catalogue of edge cases discovered in the ticket dataset
so that the production agent can handle them without crashing or producing harmful responses.

**Why this priority**: Edge cases directly impact escalation rate, accuracy score, and
customer experience — all rubric items. Each unhandled edge case is a potential failure mode.

**Independent Test**: The discovery log at `specs/discovery-log.md` lists ≥10 distinct
edge case types with ticket IDs, affected channels, and handling strategies.

**Acceptance Scenarios**:

1. **Given** the 60-ticket dataset,
   **When** edge cases are analysed,
   **Then** at least these types are identified: non-English message, gibberish/empty,
   angry negative sentiment, refund request, very long message, legal/GDPR,
   security incident, pricing negotiation, explicit human request, cross-domain same-org.

2. **Given** TKT-032 (gibberish WhatsApp message),
   **When** the agent processes it,
   **Then** the agent requests clarification without creating a ticket or calling
   any resolution tools.

3. **Given** TKT-030 (Urdu message via WhatsApp),
   **When** the agent processes it,
   **Then** language is detected as non-English and the response is either in the
   detected language or politely acknowledges the language limitation.

4. **Given** TKT-003 (billing question containing the word "charged"),
   **When** the agent evaluates escalation triggers,
   **Then** it does NOT escalate for a refund because semantic intent analysis
   identifies the question as a standard billing enquiry, not a refund request.

---

### User Story 4 — Requirement Extraction (Priority: P2)

As a developer, I need a structured list of requirements discovered from the ticket
analysis that were not explicitly stated in the project brief, so that nothing is
missed during the prototype and production build phases.

**Why this priority**: Non-obvious requirements discovered during incubation are
the primary value of the exploration phase. Missing them means bugs in production.

**Independent Test**: `specs/discovery-log.md` contains a Requirements Discovered
table with ≥10 entries, each linked to a source ticket ID.

**Acceptance Scenarios**:

1. **Given** the discovery log,
   **When** the requirements table is reviewed,
   **Then** it contains ≥14 requirements (R1–R14) each with a source ticket reference.

2. **Given** R11 (escalation must be LLM-intent-based, not keyword-based),
   **When** TKT-003 is tested against both approaches,
   **Then** keyword matching produces a false positive escalation;
   intent-based analysis correctly classifies it as a billing question.

---

### Edge Cases

- What happens when a WhatsApp customer provides only a phone number (no email)?
  → Customer identity stored by phone only; cross-channel unification impossible until
  email is provided. System must prompt for email in follow-up if cross-channel history
  would add value.

- What happens when a web form ticket message exceeds 400 words (like TKT-051)?
  → Agent summarises the message before processing. Full text stored in DB.
  Summary (≤200 words) passed to LLM to respect token budget.

- What happens when a message is in an unsupported language?
  → Language detected; agent responds in English with an apologetic note about
  language limitations and offers to connect the customer with a human agent.

- What happens when the analysis script cannot find `sample-tickets.json`?
  → Script exits with a descriptive error message indicating the expected path.

- What happens when a ticket has no `customer_email` field (null)?
  → Script skips email-based cross-channel unification for that ticket;
  channel identifier (phone for WhatsApp) used as fallback key.

## Requirements

### Functional Requirements (Exploration Phase)

- **FR-001**: System MUST provide a Python script (`src/agent/analyze_tickets.py`) that
  loads `context/sample-tickets.json` and produces a structured per-channel analysis report
  without requiring any external dependencies beyond the Python standard library.

- **FR-002**: The analysis script MUST calculate and print: ticket count per channel,
  average message length (words and characters), min/max message length, category
  distribution, sentiment distribution, and identifier (email/phone) coverage.

- **FR-003**: The analysis script MUST identify customers who appear in tickets from
  more than one channel (cross-channel customers) using email address as the join key.

- **FR-004**: The analysis script MUST identify and categorize edge cases from the ticket
  dataset across at least 8 distinct categories (non-English, gibberish, negative sentiment,
  refund, very long, legal, security, pricing negotiation).

- **FR-005**: The discovery log at `specs/discovery-log.md` MUST contain only real
  data from running the analysis script — no placeholder text or estimated values.

- **FR-006**: The discovery log MUST document the false-positive risk of keyword-based
  escalation detection, with specific ticket IDs as evidence (TKT-003, TKT-042, TKT-051).

- **FR-007**: The discovery log MUST list ≥14 requirements discovered from the analysis
  (R1–R14) with source ticket IDs and priority levels.

- **FR-008**: The discovery log MUST list ≥6 open questions that require decisions before
  the prototype build phase.

### Key Entities

- **Ticket**: Represents a single customer support message. Key attributes: id, channel,
  customer_email, customer_phone, message content, expected_category, sentiment, timestamp.

- **Channel**: One of `email`, `whatsapp`, `web_form`. Determines identifier type,
  response format, and message length norms.

- **Cross-channel Customer**: A customer whose email address appears in tickets from
  ≥2 distinct channels. Primary key: customer_email.

- **Edge Case**: A ticket exhibiting characteristics that require special handling
  beyond the standard resolution flow. Identified by content patterns, sentiment score,
  language, length, or category.

- **Discovery Log**: A markdown document (`specs/discovery-log.md`) capturing all
  findings from the exploration session. Serves as the incubation quality deliverable.

## Success Criteria

### Measurable Outcomes

- **SC-001**: The analysis script runs to completion in under 10 seconds on the
  60-ticket dataset with no errors or exceptions.

- **SC-002**: All per-channel metrics in the discovery log exactly match the script
  output (zero placeholder values, zero estimated numbers).

- **SC-003**: The discovery log identifies 100% of the cross-channel customers
  in the 60-ticket dataset (both James Okonkwo and Marcus Thompson).

- **SC-004**: The edge case catalogue covers ≥10 distinct types with ticket IDs
  and handling strategies for each.

- **SC-005**: The requirements table contains ≥14 requirements linked to source tickets,
  covering all major non-obvious discoveries from the analysis.

- **SC-006**: The discovery log is accepted as a scored deliverable contributing to
  the Incubation Quality score (10 pts rubric item) — content is iterative, specific,
  and evidenced rather than generic.

- **SC-007**: The false-positive keyword-matching issue is documented with 3+ ticket
  IDs as evidence, establishing the requirement for LLM-intent-based escalation detection.
