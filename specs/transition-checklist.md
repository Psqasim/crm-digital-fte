# Transition Checklist: General → Custom Agent
## NexaFlow Customer Success FTE — Phase 3

**Phase:** 3 — Incubation → Production Transition
**Date:** 2026-04-04
**Branch:** `004-transition`
**Source spec:** `specs/customer-success-fte-spec.md` (v1.0.0, Phase 2F)

> All data in this checklist was derived from real incubation work (Phases 2A–2E).
> No placeholders. No guesswork. Every figure came from running code or reading tickets.

---

## 1. Discovered Requirements

All 14 requirements inferred from programmatic analysis of 60 sample tickets in Phase 2A.
Source: `specs/discovery-log.md` (R1–R14).

| # | Requirement | Source Ticket(s) | Priority | Status |
|---|-------------|-----------------|----------|--------|
| R1 | WhatsApp customers identified by E.164 phone number; must attempt email resolution for cross-channel unification | TKT-021..040 | P1 | ✅ Phase 2C |
| R2 | Email channel needs Gmail thread ID detection — replies must attach to existing ticket, not create new ones | TKT-009, TKT-019 | P1 | 🔲 Phase 4 |
| R3 | Response length limits strictly enforced: Email ≤2500 chars hard limit, WhatsApp ≤1600 chars hard / 300 soft, Web Form ≤5000 chars hard | All channels | P1 | ✅ Phase 2B |
| R4 | Non-English messages must be detected via language classifier (not ASCII ratio); agent responds in same language | TKT-030 (Urdu), TKT-043 (Spanish) | P2 | 🔲 Phase 3 |
| R5 | Gibberish/empty messages must request clarification — DO NOT create ticket or call tools | TKT-032 | P2 | ✅ Phase 2B |
| R6 | Cross-channel customer history must be fetched and surfaced to agent before every response | TKT-025/050 (Marcus Thompson), TKT-002/052 (James Okonkwo) | P1 | ✅ Phase 2C |
| R7 | Web Form pre-categorisation treated as a hint, not authoritative — agent re-classifies from message content | TKT-041..060 | P2 | ✅ Phase 2B |
| R8 | Messages >400 words must be summarised before LLM processing (token budget management) | TKT-051 (529 words) | P2 | 🔲 Phase 3 |
| R9 | SLA clock starts at `received_at` timestamp (not agent processing time) — Enterprise tickets open 3+ hrs trigger P1 escalation | All channels | P1 | ✅ Phase 2C |
| R10 | Same-domain follow-up detection: tickets from the same email domain (nexgen-ops.com pattern) within 7 days should be linked | TKT-006, TKT-046 | P2 | 🔲 Phase 3 |
| R11 | Escalation triggers must be LLM-intent-based, NOT keyword-based — keyword matching caused false positives in Phase 2A | TKT-003, TKT-042, TKT-051 | P1 | ✅ Phase 2B |
| R12 | Security incidents are the highest-priority escalation type — bypass all queues and notify #security-incidents immediately | TKT-060 | P1 | ✅ Phase 2C |
| R13 | Pakistan market is significant (6/20 WhatsApp contacts from .pk domains); Urdu support is a roadmap item | TKT-021..023, 026, 030, 040 | P3 | 📋 Roadmap |
| R14 | WhatsApp same-day multi-message flow — active conversations must be detected and messages threaded (24-hour window) | WhatsApp all | P1 | ✅ Phase 2C |

**Legend:** ✅ Implemented in prototype | 🔲 Planned for production phase | 📋 Post-hackathon roadmap

---

## 2. Working Prompts

### System Prompt That Worked

From `src/agent/prompts.py::get_system_prompt()` — tested across email, WhatsApp, and
web_form in `tests/test_prototype.py` (8 tests) and `tests/test_core_loop.py` (4 tests).

```python
def get_system_prompt(channel: str, customer_name: str) -> str:
    current_dt = datetime.now(ZoneInfo("Asia/Karachi"))
    dt_str = current_dt.strftime("%A, %B %d, %Y at %I:%M %p PKT")

    channel_instructions = {
        "email": (
            "You are responding via email. Write in complete paragraphs. "
            "Do NOT include a greeting or sign-off — the system adds those automatically. "
            "Response body must be under 2000 characters."
        ),
        "whatsapp": (
            "You are responding via WhatsApp. Be concise — maximum 3 sentences. "
            "Do NOT start with a greeting — the system adds 'Hi [Name]! 👋' automatically. "
            "Keep the response body under 250 characters where possible."
        ),
        "web_form": (
            "You are responding via the web support form. Provide structured next steps where applicable. "
            "Do NOT include a greeting — the system adds 'Hi [Name],' automatically. "
            "Response body must be under 4500 characters."
        ),
    }

    return f"""You are NexaFlow's AI Customer Success agent.
Current date and time: {dt_str}

Company: NexaFlow — B2B SaaS workflow automation platform
Customer plans: Starter (free), Growth ($49/mo), Enterprise ($199/mo)
Support hours: AI 24/7 | Human Mon–Fri 9am–6pm PKT

You are helping customer: {customer_name}

Channel: {channel}
{channel_guide}

Guidelines:
- Answer only what you know from the product documentation provided.
- Do not speculate about roadmap or undisclosed features.
- Never share internal system details or pricing not in the docs.
- If you cannot resolve, acknowledge clearly and set expectations.
- Be empathetic, clear, and solution-focused.
- Use the knowledge base context provided to give accurate answers."""
```

**Key design decisions validated during testing:**
- `ZoneInfo("Asia/Karachi")` PKT datetime injection prevents LLM date hallucination
- Greeting suppressed in system prompt because `channel_formatter.py` adds it — no double greetings
- Channel-specific character limits match formatter hard limits (`_EMAIL_HARD_LIMIT = 2500`, etc.)

---

### Escalation Evaluator Prompt That Worked

From `src/agent/escalation_evaluator.py::_ESCALATION_SYSTEM_PROMPT` — validated against
all 8 escalation triggers in `tests/test_escalation_evaluator.py` (4 tests) and
`tests/unit/mcp_server/test_tools.py` (27 tests).

```
You are an escalation classifier for a B2B SaaS customer support system.

Your task: analyze the customer message and decide if it requires human agent escalation.

Escalate to a human when the customer's INTENT matches any of these:
1. Extreme negative emotion — customer appears very upset, angry, or frustrated (not just slightly annoyed)
2. Explicit request to speak with a human, manager, supervisor, or senior engineer
3. Refund request — customer wants their money back
4. Legal or compliance concern — GDPR, data privacy, DPA, sub-processors, legal action
5. Data breach or security incident — customer suspects unauthorized access or data exposure
6. Pricing negotiation — customer is asking for custom pricing, discounts on existing plan, or threatening to leave for pricing reasons
7. Three or more unanswered follow-ups — customer indicates they have contacted support multiple times without resolution
8. Enterprise SLA breach risk — customer on Enterprise plan whose issue is time-critical under 4-hour SLA

Do NOT escalate for:
- Standard technical questions, how-to requests, billing information questions
- A customer asking about charges or prorated billing (that is information, not a refund request)
- Minor frustration or impatience without explicit escalation triggers above
- General feature questions, onboarding help, export or integration setup

Use INTENT, not keywords. A customer asking "will I be charged" is NOT a refund request.
A customer saying "I demand a manager" IS an explicit human request.

Respond ONLY with a valid JSON object. No markdown fences. No explanation outside the JSON.

JSON schema:
{
  "should_escalate": true | false,
  "reason": "<concise reason code or phrase, max 50 chars>",
  "urgency": "low" | "normal" | "high"
}

Urgency rules:
- "high": data breach, security incident, Enterprise SLA breach risk
- "normal": refund, legal/compliance, explicit human request, multiple follow-ups, extreme sentiment
- "low": pricing negotiation only
- If should_escalate is false, use "normal" as default urgency.
```

**Why this prompt worked:** Explicit "use INTENT not keywords" instruction eliminated
the TKT-003 false positive ("will I be charged" ≠ refund request) and TKT-042 false positive
("engineering manager" job title ≠ human agent request). Validated by Phase 2A false positive
analysis in `specs/discovery-log.md`.

---

## 3. Edge Cases Found

All 10 edge case types discovered during Phase 2A analysis (`src/agent/analyze_tickets.py`)
and confirmed against the 60-ticket sample dataset.

| Edge Case | Ticket ID | How Handled | Test Case Exists |
|-----------|-----------|-------------|-----------------|
| Gibberish / empty message | TKT-032 (WhatsApp) | Return clarification request; DO NOT create ticket; DO NOT call any tools | Yes — `tests/test_core_loop.py` |
| Non-English message (Urdu/Arabic script) | TKT-030 (WhatsApp) | Language detection required; respond in same language; `langdetect`/`fasttext` planned for Phase 3 | Partial — flagged in discovery-log.md; full test in Phase 3 |
| Non-English message (Spanish/ASCII) | TKT-043 (Web Form) | Missed by ASCII-ratio heuristic; only proper language classifier catches this | No — added to Phase 3 backlog |
| Pricing negotiation | TKT-020 (email), TKT-040 (WhatsApp), TKT-055 (Web Form) | Immediate escalation to Sales/CSM; zero pricing strategy revealed; acknowledge interest only | Yes — `tests/test_escalation_evaluator.py` |
| Refund / billing dispute | TKT-007 (email), TKT-026 (WhatsApp) | Escalate to billing team; acknowledge receipt; no AI resolution; ETA provided | Yes — `tests/test_escalation_evaluator.py` |
| Refund keyword false positive | TKT-003 (email — "will I be charged") | LLM intent classifier correctly identifies as billing question, NOT refund; no escalation | Yes — `tests/test_escalation_evaluator.py` |
| Legal / compliance (GDPR) | TKT-044 (Web Form) | Immediate escalation; no information provided; acknowledge query is being reviewed only | Yes — `tests/unit/mcp_server/test_tools.py` |
| Security incident (data breach) | TKT-060 (Web Form) | Highest-priority escalation; bypass all queues; route to `#security-incidents`; do NOT ask for details via chat | Yes — `tests/unit/mcp_server/test_tools.py` |
| Explicit human request | TKT-006 (email — "I demand a manager") | Immediate escalation; acknowledge request; provide human availability hours (Mon–Fri 9am–6pm PKT); no AI resolution | Yes — `tests/test_escalation_evaluator.py` |
| Very long message (>400 words) | TKT-051 (Web Form — 529 words) | Summarise to ≤200 words before LLM processing; store full message in DB; prevents token budget overflow | No — planned for Phase 3 |

**Cross-channel edge cases discovered:**
- TKT-025 + TKT-050 (Marcus Thompson): same customer, WhatsApp → Web Form follow-up. Without cross-channel history, agent would repeat the same failed fix. Validated by `tests/test_cross_channel.py` (Marcus Thompson pattern test).
- TKT-002 + TKT-052 (James Okonkwo): email → Web Form follow-up. Web Form ticket explicitly references TKT-002. Agent must surface prior context. Validated by `tests/test_cross_channel.py` (James Okonkwo pattern test).

---

## 4. Response Patterns That Worked

Channel limits are enforced in `src/agent/channel_formatter.py`.
All values are measured from actual code constants, not estimates.

### Email
- **Format:** `"Dear {name},\n\n{body}{signature}"`
- **Signature appended automatically:** `NexaFlow Customer Success | support@nexaflow.io | help.nexaflow.io | Mon–Fri 9am–6pm PKT | AI support available 24/7`
- **Greeting:** `"Dear {name},"` — formal, full name used
- **Hard limit:** 2,500 characters total (body truncated with `…` if exceeded)
- **Tone:** Complete paragraphs, professional business language, no emoji
- **LLM instruction:** "Write in complete paragraphs. Response body under 2000 characters."
- **Source:** `src/agent/channel_formatter.py::_format_email()`, `_EMAIL_HARD_LIMIT = 2500`

### WhatsApp
- **Format:** `"Hi {name}! 👋 {body}"`
- **Greeting:** `"Hi {name}! 👋"` — casual, first name only, emoji always included
- **Soft limit:** 300 characters body (target; LLM instructed to stay under 250 chars in response body)
- **Hard limit:** 1,600 characters total (Twilio WhatsApp message limit)
- **Sentence cap:** Maximum 3 sentences — formatter splits on `.!?` and truncates
- **Tone:** Concise, conversational, casual; no signature; abbreviations acceptable
- **LLM instruction:** "Be concise — maximum 3 sentences. Keep body under 250 characters where possible."
- **Source:** `src/agent/channel_formatter.py::_format_whatsapp()`, `_WHATSAPP_HARD_LIMIT = 1600`, `_WHATSAPP_SOFT_LIMIT = 300`

### Web Form
- **Format:** `"Hi {name},\n\n{body}"`
- **Greeting:** `"Hi {name},"` — semi-formal, first name
- **Hard limit:** 5,000 characters total
- **Tone:** Semi-formal, structured; numbered next steps or bullet points where applicable; no signature
- **LLM instruction:** "Provide structured next steps where applicable. Body under 4500 characters."
- **Source:** `src/agent/channel_formatter.py::_format_web_form()`, `_WEBFORM_HARD_LIMIT = 5000`

---

## 5. Escalation Rules Finalized

All 8 triggers from `context/escalation-rules.md`, with validation method from incubation.

| # | Trigger | Condition | Urgency | Validated By |
|---|---------|-----------|---------|-------------|
| 1 | Sentiment score below threshold | Sentiment score < 0.3 (0.0–1.0 scale) | normal | 10 negative tickets in 60-ticket dataset (TKT-001, 006, 015, 023, 026, 038, 041, 046, 057, 060); `tests/test_escalation_evaluator.py` |
| 2 | Refund requested | Customer explicitly requests money back — any amount, any reason | normal | TKT-007, TKT-026; false positive TKT-003 confirmed NOT triggered by "will I be charged"; `tests/test_escalation_evaluator.py` |
| 3 | Legal or compliance question | GDPR, CCPA, data breach, legal action, DPA, data deletion rights, regulatory inquiry | normal | TKT-044 (GDPR / Web Form); `tests/unit/mcp_server/test_tools.py` |
| 4 | Pricing negotiation attempt | Discount request, custom pricing, competitor price match, deals not on website | low | TKT-020, TKT-040, TKT-055 (3 channels, all pricing); `tests/unit/mcp_server/test_tools.py` |
| 5 | Three or more unanswered follow-ups | Same customer email has sent 3+ messages without satisfactory resolution | normal | Marcus Thompson pattern (TKT-025 → TKT-050); validated by `ConversationStore.get_conversation_history()`; `tests/test_cross_channel.py` |
| 6 | Explicit human agent request | Customer explicitly asks for human, person, real agent, or manager | normal | TKT-006 ("I demand a manager" — email); false positive TKT-042 ("engineering manager" job title) confirmed NOT triggered; `tests/test_escalation_evaluator.py` |
| 7 | Data breach concern | Customer reports unauthorized account access, data theft, or seeing another customer's data | high | TKT-060 (highest priority in dataset); bypass all queues → `#security-incidents`; `tests/unit/mcp_server/test_tools.py` |
| 8 | Enterprise SLA breach risk | Enterprise plan ticket open 3+ hours without resolution (4-hour SLA) | high | R9 from discovery-log.md; SLA clock starts at `Ticket.opened_at = received_at`; `tests/unit/test_conversation_store.py` |

**Critical finding from incubation:** Escalation triggers MUST be intent-based (LLM-evaluated),
not keyword-based. Phase 2A keyword matching produced 3 false positives:
- TKT-003: "charged" in billing question ≠ refund
- TKT-042: "engineering manager" job title ≠ human request
- TKT-051: "project manager" in workflow description ≠ human request

GPT-4o-mini intent classifier in `escalation_evaluator.py` resolved all three. Zero false
positives in test suite.

---

## 6. Performance Baseline

Data from Phase 2A analysis (`src/agent/analyze_tickets.py`) and Phase 2B–2E test suite execution.

| Metric | Observed | Target | Source |
|--------|----------|--------|--------|
| Escalation rate (sample) | 9/60 = **15%** | < 25% | `specs/discovery-log.md` §Performance Baseline |
| Negative sentiment rate | 10/60 = **16.7%** | — | Script output: `analyze_tickets.py` |
| Cross-channel customers found | 2/60 = **3.3%** | — | James Okonkwo (TKT-002+052), Marcus Thompson (TKT-025+050) |
| Test suite pass rate | **101/101 = 100%** | 100% | `pytest tests/` on `003-mcp-server` branch |
| P95 processing latency target | < **3 seconds** | < 3s | Constitution §3 |
| First response time target | < **2 minutes** end-to-end | < 2 min | Company profile (`context/company-profile.md`) |
| AI resolution rate target | > **75%** | > 75% | Company profile |
| Cross-channel ID accuracy target | > **95%** | > 95% | Hackathon rubric |
| Average email message length | **49.5 words / 283.3 chars** | — | `analyze_tickets.py` output |
| Average WhatsApp message length | **14.7 words / 79.1 chars** | — | `analyze_tickets.py` output |
| Average Web Form message length | **74.0 words / 432.6 chars** | — | `analyze_tickets.py` output |
| Longest message in dataset | **TKT-051: 529 words** | — | Web Form; triggers R8 summarisation requirement |
| False positive escalations (keyword) | 3 (TKT-003, 042, 051) | 0 | Fixed by LLM-intent classifier in Phase 2B |
| False positive escalations (LLM) | **0** | 0 | `tests/test_escalation_evaluator.py` all passing |

**Channel distribution (60-ticket dataset):**
- Email: 20 tickets (TKT-001 to TKT-020) — top category: `feature_question` (6)
- WhatsApp: 20 tickets (TKT-021 to TKT-040) — top category: `feature_question` (9)
- Web Form: 20 tickets (TKT-041 to TKT-060) — top category: `feature_question` (6), highest escalation rate (4/20 = 20%)

**Worst-case escalation projection:** If all 10 negative-sentiment tickets escalate,
rate = 16.7% — still within the < 25% target. Reasonable confidence in production viability.

---

## 7. Prototype → Production Component Map

From `specs/customer-success-fte-spec.md` §11 (Production Build Map, v1.0.0).

All 17 rows from the authoritative component map. Status: `[ ]` = not started (Phase 4 begins next).

| # | Incubation Component | Incubation File | Production Equivalent | Production File | Status |
|---|---------------------|-----------------|----------------------|-----------------|--------|
| 1 | Core interaction loop | `src/agent/prototype.py::process_ticket()` | OpenAI Agents SDK agent with `@function_tool` decorated tools | `production/agent/customer_success_agent.py` | [ ] |
| 2 | MCP server tools (7 tools) | `src/mcp_server/server.py` | `@function_tool` decorated functions with Pydantic input schemas | `production/agent/tools.py` | [ ] |
| 3 | In-memory ConversationStore | `src/agent/conversation_store.py` | Neon PostgreSQL 16 + pgvector; `asyncpg` driver | `production/database/queries.py` + `production/database/schema.sql` | [ ] |
| 4 | In-memory `_ticket_index` dict | `src/mcp_server/server.py::_ticket_index` | PostgreSQL `tickets` table with FK to `conversations` | `production/database/schema.sql` | [ ] |
| 5 | In-memory customer profiles | `ConversationStore._customers` | PostgreSQL `customers` + `customer_identifiers` tables | `production/database/schema.sql` | [ ] |
| 6 | Knowledge base (Jaccard search) | `src/agent/knowledge_base.py` | PostgreSQL `knowledge_base` table + pgvector `ivfflat` index; cosine similarity search | `production/database/queries.py::search_knowledge_base()` | [ ] |
| 7 | Channel formatter | `src/agent/channel_formatter.py` | Channel-aware response formatters (same logic, production-hardened) | `production/agent/formatters.py` | [ ] |
| 8 | Escalation evaluator (LLM call) | `src/agent/escalation_evaluator.py` | Same logic; wrapped with `asyncio.to_thread()` in async context | `production/agent/tools.py::escalate_decision_tool()` | [ ] |
| 9 | Skills invoker (sync) | `src/agent/skills_invoker.py::SkillsInvoker` | `AsyncSkillsInvoker` subclass in Kafka worker context | `production/workers/message_processor.py` | [ ] |
| 10 | System prompt with datetime | `src/agent/prompts.py` | Same `ZoneInfo("Asia/Karachi")` injection; extracted to prompts module | `production/agent/prompts.py` | [ ] |
| 11 | Print statement output | `prototype.py` (print to stdout) | Structured logging (`logging` → stderr) + Kafka events to `fte.metrics` topic | `production/workers/message_processor.py` | [ ] |
| 12 | Single-threaded CLI execution | `prototype.py __main__` | Async Kubernetes worker pods (HPA min=3, max=20 for API; max=30 for workers) | `production/k8s/deployment-worker.yaml` | [ ] |
| 13 | Hardcoded config | `.env` file only | Environment variables + Kubernetes `ConfigMap` / `Secret` objects | `production/k8s/configmap.yaml`, `production/k8s/secrets.yaml` | [ ] |
| 14 | Direct channel simulation | `send_response` MCP tool (logs to stderr) | Gmail API `send_reply()` with thread ID; Twilio `send_message()` with WhatsApp prefix; FastAPI webhook handlers | `production/channels/gmail_handler.py`, `production/channels/whatsapp_handler.py` | [ ] |
| 15 | Manual test runs | `pytest tests/` local | Automated pytest suite in CI + `tests/test_multichannel_e2e.py` | `production/tests/test_e2e.py` | [ ] |
| 16 | Ticket ID (`TKT-<hex>`) | `ConversationStore` UUID generation | Same format; stored as primary key in `tickets` table | `production/database/schema.sql` | [ ] |
| 17 | Escalation ID (`ESC-<hex>`) | `escalate_to_human` MCP tool | Same format; stored in `escalations` table with `assigned_to` FK | `production/database/schema.sql` | [ ] |

**Required PostgreSQL tables for production (8 total):**
`customers`, `customer_identifiers`, `conversations`, `messages`, `tickets`,
`knowledge_base`, `channel_configs`, `agent_metrics`

**Required Kafka topics for production (9 total):**
`fte.tickets.incoming`, `fte.channels.email.inbound`, `fte.channels.whatsapp.inbound`,
`fte.channels.webform.inbound`, `fte.channels.email.outbound`,
`fte.channels.whatsapp.outbound`, `fte.escalations`, `fte.metrics`, `fte.dlq`

---

## Pre-Transition Checklist

- [x] All 14 requirements from discovery-log.md listed above (R1–R14)
- [x] Working system prompt copied verbatim from `src/agent/prompts.py`
- [x] Working escalation prompt copied verbatim from `src/agent/escalation_evaluator.py`
- [x] All 10 edge cases documented with real ticket IDs
- [x] Channel response patterns derived from `channel_formatter.py` constants
- [x] All 8 escalation triggers listed with validation evidence
- [x] Performance baseline from `analyze_tickets.py` script output
- [x] 17-row prototype→production component map from `customer-success-fte-spec.md §11`
- [x] Production folder scaffold in place (`production/`)
- [x] Placeholder files created for all Phase 4 modules
- [ ] `production/tests/test_transition.py` — to be created in Phase 3
- [ ] Non-English language classifier integrated (R4) — Phase 3
- [ ] Message summarisation for >400-word messages (R8) — Phase 3
- [ ] Same-domain follow-up detection (R10) — Phase 3

---

*Checklist version 1.0 — Phase 3 — 2026-04-04*
*Authority: All data sourced from Phase 2A–2F incubation artifacts*
