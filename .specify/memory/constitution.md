<!--
SYNC IMPACT REPORT
==================
Version change: (blank template) → 1.0.0
Modified principles: N/A — initial population from blank template
Added sections:
  - I.   Project Purpose & Business Problem
  - II.  Digital FTE Definition & Cost Contract
  - III. Multi-Channel Architecture Principles
  - IV.  Agent Behavioral Contract (Non-Negotiable Rules)
  - V.   Escalation Contract
  - VI.  Technology Stack (Locked Decisions)
  - §2.  Scoring-Driven Priorities & Phase Contracts
  - §3.  Definition of Done
  - Governance
Removed sections: All template placeholder comments (replaced with real content)
Templates requiring updates:
  ✅ .specify/memory/constitution.md — populated (this file)
  ⚠  .specify/templates/plan-template.md — pending review for constitution alignment
  ⚠  .specify/templates/spec-template.md — pending review for constitution alignment
  ⚠  .specify/templates/tasks-template.md — pending review for constitution alignment
Follow-up TODOs: None — all fields resolved
-->

# CRM Digital FTE Factory Constitution

## Core Principles

### I. Project Purpose & Business Problem

This project builds a production-grade AI Customer Success agent (Digital FTE) for **NexaFlow** —
a B2B SaaS workflow automation platform serving 3,000 active accounts across US, UK, Pakistan,
and India. NexaFlow processes ~800 tickets/week across three channels (Gmail, WhatsApp, Web Form).
A human FTE costs $75,000/year and works only during business hours (Mon–Fri 9am–6pm PKT).

The Digital FTE MUST solve:

- Unified ticket intake from three heterogeneous channels into a single processing pipeline
- Customer identity resolution across all channels (email as primary key, phone as secondary)
- Context-aware, empathetic, channel-appropriate AI responses with <2 min first response time
- Intelligent escalation to human agents for 8 defined trigger conditions
- Measurable SLA compliance per customer plan tier (Starter / Growth / Enterprise)
- Achieve 75% AI resolution rate without human escalation at <$1,000/year operating cost

This is both a hackathon submission (GIAIC Hackathon 5, scored on a 100-point rubric) and a
blueprint for a real production system. Every design decision MUST serve both goals.

### II. Digital FTE Definition & Cost Contract

A "24/7 AI Customer Success FTE" is defined as follows:

**What it IS:**
- Available 24 hours/day, 365 days/year — no downtime, sick days, or vacations
- Handles 75%+ of support tickets autonomously without human escalation
- Total operating cost target: <$1,000/year (compute + OpenAI API + cloud storage)
- AI first response time: <2 minutes from ticket submission
- Learns from resolved tickets via vector knowledge base (pgvector semantic search)

**What it is NOT:**
- A replacement for human judgment on complex, legal, financial, or emotionally critical issues
- A full website — only the Web Support Form component is in scope
- An integration with external CRMs (Salesforce, HubSpot) — the PostgreSQL schema IS the CRM
- A production WhatsApp Business account — Twilio Sandbox is used for development

**Cost comparison:**

| Resource     | Human FTE       | Digital FTE     |
|--------------|-----------------|-----------------|
| Annual cost  | $75,000+        | <$1,000         |
| Availability | Mon–Fri 9–6 PKT | 24/7/365        |
| Consistency  | Variable        | Deterministic   |
| Scale        | Linear cost     | Near-zero marginal cost |

### III. Multi-Channel Architecture Principles

These rules govern how messages enter, flow through, and exit the system. ALL are NON-NEGOTIABLE.

**Rule III-1 — Unified Ingestion via Kafka:** Every message, regardless of source channel, MUST be
normalized into a unified ticket event and published to the `fte.tickets.incoming` Kafka topic
before agent processing. No channel may bypass the queue. This is the single entry point.

**Rule III-2 — Customer Identity Unification:** Customer identity MUST be unified by email address
as the primary key. Phone number (WhatsApp) is a secondary identifier linked via the
`customer_identifiers` table. A customer record is created on first contact and reused across all
subsequent interactions on any channel. Cross-channel identity linking is a core feature, not
optional, and is scored under Cross-Channel Continuity (10 pts).

**Rule III-3 — Channel Metadata Preservation:** Every stored message and ticket MUST preserve its
source channel (`email`, `whatsapp`, `web_form`) and the external message ID (Gmail message ID,
Twilio MessageSid, etc.). Channel metadata MUST NEVER be lost, overwritten, or inferred.

**Rule III-4 — Channel-Adaptive Responses:** Response style MUST adapt to the delivery channel:

| Channel   | Greeting              | Tone         | Max Length      | Sign-off        |
|-----------|-----------------------|--------------|-----------------|-----------------|
| Email     | "Dear [FirstName],"   | Formal       | 500 words       | NexaFlow signature |
| WhatsApp  | "Hi [FirstName]! 👋"  | Conversational | 300 chars pref / 1600 max | Natural ("Let me know!") |
| Web Form  | "Hi [FirstName],"     | Semi-formal  | 1000 chars / 300 words | Support link    |

WhatsApp: max 1 emoji per message; acceptable: ✅ 👋 😊; prohibited: 🔥 💯 🎉 🚀.

**Rule III-5 — Three-Channel Completeness:** All three channels MUST be implemented. The Web
Support Form is the highest-priority deliverable (10 pts, never skip). Gmail and WhatsApp are
expected; partial implementations must be documented with known limitations.

### IV. Agent Behavioral Contract (Non-Negotiable Rules)

These rules are hard-coded into the agent system prompt. Violation of any rule is a defect.

**ALWAYS — Required behaviors:**

1. **Inject current datetime** using `datetime.now(ZoneInfo("Asia/Karachi"))` into every system
   prompt invocation. The agent MUST NEVER guess or infer the current date from training data.
   Required for: SLA breach detection, correct timestamps, scheduling context.

2. **Create ticket first:** Call `create_ticket` BEFORE generating any customer response. Enforced
   tool call order: `create_ticket` → `get_customer_history` → `search_knowledge_base` (if needed)
   → `send_response`. Responding without a ticket is a protocol violation.

3. **Check full cross-channel history:** Call `get_customer_history` on every interaction.
   If a customer has contacted before on any channel, acknowledge it in the response.

4. **Analyze sentiment before closing:** Every ticket close MUST have a sentiment score recorded.
   Tickets with sentiment < 0.3 MUST escalate before closure.

5. **Use customer's first name** at least once per response.

6. **Acknowledge frustration before solutions:** If the customer is clearly upset, the first
   sentence MUST validate their experience before offering help.

7. **End with a help offer:** Every response ends with an offer to assist further.

**NEVER — Prohibited behaviors:**

1. Discuss competitor products by name or implication: Asana, Monday.com, ClickUp, Notion,
   Trello, Basecamp, Linear, Jira (as project tool), Airtable, Smartsheet.

2. Promise unreleased features. If asked about the roadmap: "I'm not able to share details about
   upcoming features, but I'd love to pass your feedback to our product team."

3. Reveal internal pricing strategies, discount thresholds, or negotiation flexibility.

4. Guess the current date from training data. Always use the injected datetime.

5. Respond to a customer without calling the `send_response` tool.

6. Exceed channel limits: Email ≤500 words, WhatsApp ≤1600 chars, Web Form ≤1000 chars.

7. Say "I don't know" — say "Let me look into that for you" or "Great question — here's what
   I can tell you" instead.

8. Reveal internal system details, tool names, or processing architecture to customers.

### V. Escalation Contract

The agent MUST escalate (flag ticket, notify appropriate Slack channel, send acknowledgment to
customer) when ANY of the following conditions are met:

| # | Trigger | Condition | Notify |
|---|---------|-----------|--------|
| 1 | Sentiment breach | Sentiment score < 0.3 | #support-escalations |
| 2 | Refund request | Any explicit refund mention | #billing-escalations |
| 3 | Legal/compliance | GDPR, CCPA, breach, lawsuit, subpoena, DPA | #support-escalations (no extra info) |
| 4 | Pricing negotiation | Discount, custom pricing, competitor price match | Sales/CSM team |
| 5 | 3+ unanswered follow-ups | Same customer (by email), 3+ messages without resolution | #support-escalations |
| 6 | Explicit human request | "speak to a human", "real agent", "manager" | Acknowledge + queue |
| 7 | Data breach concern | Unauthorized access, data theft, wrong data visible | #security-incidents (immediate) |
| 8 | Enterprise SLA breach risk | Enterprise ticket open 3+ hours (SLA = 4 hrs) | On-call CSM (P1) |

**Escalation logging (required):** Every escalation MUST be written to the database with:
`ticket_id`, `customer_email`, `escalation_reason` (enum: sentiment/refund/legal/pricing/
followup/human_request/security/sla_breach), `escalated_at` (UTC timestamp),
`ai_conversation_summary` (last 3 AI messages), `assigned_to` (human agent, post-assignment).

**Do NOT escalate for:** simple how-to questions, password resets, plan feature inquiries,
standard bug reports with known fixes, or integration setup help — even if customer tone is
frustrated — unless sentiment score drops below 0.3.

**Escalation framing (brand voice):** Frame escalation as a service upgrade, never as an AI
limitation. Example: "I want to make sure you get the best possible help, so I'm connecting
you with a specialist."

### VI. Technology Stack (Locked Decisions)

These choices are locked. No substitutions without a documented ADR approved by the project lead.

| Layer | Technology | Constraint |
|-------|------------|------------|
| Agent Runtime | OpenAI Agents SDK (`agents` package) | NOT LangChain, NOT raw API calls |
| LLM Model | GPT-4o via OpenAI | Cost-justified at <$1,000/yr at ~800 tickets/week |
| API Server | FastAPI (async, Python 3.12) | Must use Pydantic v2 models and Depends() |
| Database | Neon PostgreSQL 16 + pgvector | Serverless; vector index required on knowledge_base.embedding |
| Message Queue | Apache Kafka (aiokafka) | Topics: fte.tickets.incoming + 8 channel/metrics topics |
| Frontend | Next.js 15 App Router | Web Support Form only — standalone embeddable component |
| Email Channel | Gmail API (OAuth 2.0) + Pub/Sub or polling | Pub/Sub preferred for production |
| WhatsApp Channel | Twilio WhatsApp API (Sandbox for dev) | Webhook signature validation (X-Twilio-Signature) required |
| Containerization | Docker | All services containerized; no bare-metal |
| Orchestration | Kubernetes (Minikube local / Oracle Cloud VM prod) | HPA min=3, max=20 (API) / max=30 (workers) |

**Datetime rule (enforced):**
- Agent system prompts: `datetime.now(ZoneInfo("Asia/Karachi"))` → PKT-aware string
- Database/Kafka events: `datetime.utcnow().isoformat()` → UTC ISO-8601

**Secrets policy:** All credentials MUST be stored in environment variables and Kubernetes Secrets.
Never hardcode API keys, tokens, or passwords. Use `.env` for local development (gitignored).

## Scoring-Driven Priorities & Phase Contracts

### Hackathon Scoring Rubric (100 points total)

Development priority is explicitly ordered by rubric weight. Never skip Web Support Form.

**Technical Implementation — 50 pts**

| Criteria | Pts | "Done" definition |
|----------|-----|-------------------|
| Incubation Quality | 10 | `specs/discovery-log.md` documents iterative exploration; multi-channel patterns identified; edge cases catalogued |
| Agent Implementation | 10 | All 5+ tools functional with Pydantic schemas; channel-aware responses; error handling present; tool call order enforced |
| **Web Support Form** | **10** | **Complete Next.js/React form: name, email, subject, category, priority, message; client-side validation; async submission; ticket ID shown on success; status polling** |
| Channel Integrations | 10 | Gmail webhook handler + reply works; WhatsApp/Twilio handler + reply works; webhook signatures validated |
| Database & Kafka | 5 | All 8 tables created; pgvector index on embeddings; 9 Kafka topics operational; events flowing end-to-end |
| Kubernetes Deployment | 5 | All 8 manifests apply cleanly; HPA configured; liveness/readiness probes pass; pods survive restart |

**Operational Excellence — 25 pts**

| Criteria | Pts | "Done" definition |
|----------|-----|-------------------|
| 24/7 Readiness | 10 | Survives pod kills every 2 hrs; HPA scales under load; no single point of failure; dead-letter queue operational |
| Cross-Channel Continuity | 10 | Customer unified by email across channels; history visible to agent; cross-channel acknowledgment in responses |
| Monitoring | 5 | `/metrics/channels` endpoint returns per-channel stats; `agent_metrics` table populated; escalation rate alert configured |

**Business Value — 15 pts**

| Criteria | Pts | "Done" definition |
|----------|-----|-------------------|
| Customer Experience | 10 | Channel-appropriate tone per brand voice guide; all 8 escalation triggers fire correctly; sentiment analysis on every ticket close |
| Documentation | 5 | Deployment guide in README; API docs at /docs (FastAPI auto-gen); Web Form integration guide |

**Innovation — 10 pts**

| Criteria | Pts | "Done" definition |
|----------|-----|-------------------|
| Creative Solutions | 5 | Novel UX enhancements to Web Form; real-time status updates; enhanced edge case handling |
| Evolution Demonstration | 5 | Clear prototype → production progression documented in `specs/transition-checklist.md` |

**Build priority order (highest → lowest):**
Web Support Form → Incubation Quality → Agent Implementation → Channel Integrations →
24/7 Readiness → Cross-Channel Continuity → Customer Experience → Database & Kafka →
Kubernetes Deployment → Monitoring → Documentation → Creative Solutions → Evolution Demo.

### Incubation Phase Contract (Stage 1, Hours 1–16)

Required deliverables before proceeding to Stage 2. All must exist and be non-trivial.

- [ ] `specs/discovery-log.md` — iterative exploration log; channel-specific patterns; questions
  surfaced to the user
- [ ] `specs/customer-success-fte-spec.md` — crystallized spec with: supported channels table,
  in-scope / out-of-scope boundary, tools table, performance requirements, guardrails
- [ ] `specs/transition-checklist.md` — documented edge cases (≥10), working system prompts,
  finalized escalation rules, performance baseline (response time, accuracy, escalation rate)
- [ ] Working Python prototype handling customer queries from all 3 channels (basic loop:
  receive → normalize → search docs → respond → check escalation)
- [ ] MCP server (`src/mcp_server.py`) with ≥5 tools: `search_knowledge_base`, `create_ticket`,
  `get_customer_history`, `escalate_to_human`, `send_response`
- [ ] Agent skills manifest (`src/agent/skills_manifest.py` or `.json`) defining: Knowledge
  Retrieval, Sentiment Analysis, Escalation Decision, Channel Adaptation, Customer Identification
- [ ] Channel-specific response templates discovered and documented (email / WhatsApp / web)
- [ ] Test dataset: ≥20 edge cases per channel (≥60 total) in `tests/edge_cases/`
- [ ] Performance baseline measured and recorded in `specs/transition-checklist.md`

### Production Phase Contract (Stage 2, Hours 17–40)

Required production components and acceptance criteria before Stage 3 (Integration & Testing).

| Component | Acceptance Criteria |
|-----------|---------------------|
| PostgreSQL schema | 8 tables: customers, customer_identifiers, conversations, messages, tickets, knowledge_base, channel_configs, agent_metrics; ivfflat index on knowledge_base.embedding |
| OpenAI Agents SDK agent | `@function_tool` on all tools; Pydantic input schemas; enforced tool call order; PKT datetime injected on every run |
| FastAPI API server | Endpoints: POST /webhooks/gmail, POST /webhooks/whatsapp, POST /support/submit, GET /support/ticket/{id}, GET /customers/lookup, GET /metrics/channels, GET /health |
| Gmail integration | Pub/Sub webhook handler; `send_reply` with thread ID threading; email extraction from From header |
| WhatsApp integration | Twilio signature validation; `process_webhook` normalizes message; `send_message` with WhatsApp format prefix; message splitting for >1600 chars |
| Web Support Form | Next.js 15 App Router component; all 5 categories; priority selector; async POST; ticket ID shown; "Submit Another" reset; ARIA labels for accessibility |
| Kafka event streaming | 9 topics implemented: fte.tickets.incoming, fte.channels.{email/whatsapp/webform}.inbound, fte.channels.{email/whatsapp}.outbound, fte.escalations, fte.metrics, fte.dlq |
| Kubernetes manifests | 8 files: namespace.yaml, configmap.yaml, secrets.yaml, deployment-api.yaml, deployment-worker.yaml, service.yaml, ingress.yaml, hpa.yaml |
| Monitoring | /metrics/channels returns per-channel stats; agent_metrics table populated after each message; alert threshold: escalation_rate > 25%, P95 latency > 3s |
| E2E test suite | `tests/test_multichannel_e2e.py`: TestWebFormChannel, TestEmailChannel, TestWhatsAppChannel, TestCrossChannelContinuity, TestChannelMetrics all implemented |

## Definition of Done

The system is "done" when it passes the **24-Hour Multi-Channel Continuous Operation Test**:

**Volume targets (minimum):**
- 100+ Web Form submissions processed end-to-end
- 50+ Gmail emails received, processed, and replied to
- 50+ WhatsApp messages received, processed, and replied to
- 10+ customers identified across 2+ channels (cross-channel continuity verified)

**Reliability targets:**
- Uptime >99.9% (≤1.4 minutes downtime in 24 hours)
- Survives random pod kills every 2 hours (chaos testing via `kubectl delete pod`)
- Zero message loss (every Kafka-published event reaches the agent and produces a response or
  dead-letter entry)

**Performance targets:**
- P95 processing latency: <3 seconds (all channels)
- First response time (end-to-end): <2 minutes from ticket submission
- AI resolution rate: >75% (escalation rate <25%)
- Cross-channel customer identification accuracy: >95%

**Quality targets:**
- All 8 escalation triggers fire correctly on synthetic test cases
- Channel-appropriate tone verified by manual spot-check (10 responses per channel)
- Zero competitor names in any stored response
- Zero unreleased feature promises in any stored response
- Sentiment score recorded for every closed ticket

When all of the above pass simultaneously in a single 24-hour window, the Digital FTE is
production-ready.

## Governance

**Authority:** This constitution supersedes all other development practices, coding standards,
and informal conventions for the CRM Digital FTE Factory project. In any conflict between
this document and another guide, this document wins — unless the other guide was updated
after this file's `LAST_AMENDED_DATE`, in which case open an amendment.

**Amendment Procedure:**
1. Propose the change with rationale (PR description or ADR).
2. Assess version bump type: MAJOR (removes/redefines existing principle), MINOR (adds section
   or materially expands guidance), PATCH (clarification, wording, typo).
3. Update `CONSTITUTION_VERSION`, `LAST_AMENDED_DATE`, and the Sync Impact Report comment.
4. Propagate changes to all templates flagged as "⚠ pending" in the Sync Impact Report.
5. Never auto-create ADRs — suggest with: "📋 Architectural decision detected: <brief>.
   Document? Run `/sp.adr <title>`"

**Versioning policy:**
- MAJOR: Breaking governance change (e.g., swap OpenAI SDK for LangChain)
- MINOR: New principle, section, or materially expanded guidance added
- PATCH: Clarifications, wording fixes, non-semantic refinements

**Compliance gate:** Every PR touching agent logic, channel handlers, escalation rules, or
database schema MUST include a checklist confirming alignment with Principle IV (Agent
Behavioral Contract) and Principle V (Escalation Contract).

**PHR requirement:** Every user prompt triggers a Prompt History Record under
`history/prompts/` per the routing rules in `CLAUDE.md`.

**Runtime guidance:** See `CLAUDE.md` for Claude Code operating rules, ADR suggestion
procedures, and PHR creation requirements.

**Version**: 1.0.0 | **Ratified**: 2026-04-01 | **Last Amended**: 2026-04-01
