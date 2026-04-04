# Implementation Plan: Phase 2B — Prototype Core Loop

**Branch**: `001-incubation-exploration` | **Date**: 2026-04-01 | **Spec**: [spec.md](./spec.md)
**Phase**: 2B — Incubation Exercise 1.2: Prototype Core Loop (Hackathon Hours 3–8)

---

## Summary

Build a self-contained Python prototype (`src/agent/prototype.py`) that implements the
complete customer support core loop: receive a message with channel metadata →
normalize it → search product documentation → generate a channel-appropriate AI response →
decide escalation via LLM-intent detection (not keyword matching) → output the result.
This is the incubation prototype, not the production agent. It uses OpenAI chat completions
directly (no Agents SDK yet), in-memory state, and simple text-search over product docs.
The primary learning goal is to discover edge cases, validate prompts, and establish a
performance baseline before the production rewrite in Stage 2.

---

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: `openai>=1.0`, `python-dotenv` (already in project or to be added)
**Storage**: In-memory only (no DB for prototype) + `context/product-docs.md` as knowledge base
**Testing**: Manual testing via CLI + verification against 5 sample tickets from Phase 2A
**Target Platform**: Local Linux (WSL2) — no containers for prototype
**Project Type**: Single Python module with CLI entry point
**Performance Goals**: <10s total response time per ticket (prototype, not production target)
**Constraints**: Zero external services except OpenAI API; no Kafka, no Postgres, no Redis
**Scale/Scope**: Handles one ticket at a time; stateless between invocations (no session memory)

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Checked against `.specify/memory/constitution.md`.*

| Principle | Requirement | This Plan | Status |
|-----------|-------------|-----------|--------|
| IV — Agent Behavioral Contract | Inject PKT datetime into every system prompt | `datetime.now(ZoneInfo("Asia/Karachi"))` injected in every agent call | ✅ PASS |
| IV — Agent Behavioral Contract | Create ticket BEFORE generating response | `create_ticket()` called at loop start (in-memory for prototype) | ✅ PASS |
| IV — Agent Behavioral Contract | NEVER use keyword matching for escalation | LLM-intent call with structured JSON output | ✅ PASS |
| IV — Agent Behavioral Contract | NEVER mention competitors | System prompt includes competitor blocklist | ✅ PASS |
| III — Multi-Channel Arch | Normalize ALL channels to unified format | `normalize_message()` function handles all 3 channels | ✅ PASS |
| III — Multi-Channel Arch | Channel metadata NEVER lost | `NormalizedTicket` preserves source channel and all metadata | ✅ PASS |
| III — Multi-Channel Arch | Response style adapts to channel | `ChannelFormatter` applies email/whatsapp/web rules | ✅ PASS |
| VI — Tech Stack | Python 3.12 | Locked ✅ | ✅ PASS |
| VI — Tech Stack | Note: Kafka, Postgres, OpenAI Agents SDK are PRODUCTION components | Prototype intentionally omits them — documented deviation | ✅ JUSTIFIED |

**Complexity justification**: The prototype omits Kafka and Postgres as an intentional
incubation-phase simplification. Constitution §8 (Incubation Phase Contract) explicitly
allows a working prototype with in-memory state. Production components are locked for Stage 2.

---

## Project Structure

### Documentation (this feature)

```text
specs/001-incubation-exploration/
├── plan.md              # This file (/sp.plan command output)
├── research.md          # Phase 0 output — all unknowns resolved
├── data-model.md        # Phase 1 output — data types and flow
├── quickstart.md        # Phase 1 output — run the prototype in 5 min
├── contracts/
│   ├── ticket-input.json       # Input schema: TicketMessage
│   └── agent-response.json     # Output schema: AgentResponse
└── tasks.md             # Phase 2 output (/sp.tasks — not created by /sp.plan)
```

### Source Code (repository root)

```text
src/
├── agent/
│   ├── __init__.py
│   ├── analyze_tickets.py       # Phase 2A (already exists)
│   ├── prototype.py             # Phase 2B — core loop (to be built)
│   ├── models.py                # Dataclasses: TicketMessage, NormalizedTicket, AgentResponse
│   ├── knowledge_base.py        # Simple text search over product-docs.md
│   ├── channel_formatter.py     # Format response per channel rules
│   ├── escalation_evaluator.py  # LLM-intent escalation detection
│   └── prompts.py               # System prompt templates with PKT datetime injection
├── __init__.py

context/
├── product-docs.md              # Knowledge base source (already exists)
├── sample-tickets.json          # Test data (already exists)

tests/
└── test_prototype.py            # Manual verification test script

.env.example                     # OPENAI_API_KEY placeholder (no secrets committed)
```

**Structure Decision**: Single project, existing `src/agent/` directory extended with
prototype files. No new top-level directories needed. All prototype code co-located
with analysis script from Phase 2A.

---

## Implementation Tasks

### T1 — Project Setup & Environment (Priority: P0, Effort: S)

**Goal**: Ensure dependencies are declared and `.env` handling is in place.

**Files**:
- `requirements.txt` — add `openai>=1.0`, `python-dotenv`
- `.env.example` — add `OPENAI_API_KEY=sk-your-key-here`
- `src/__init__.py` — create if missing
- `src/agent/__init__.py` — create if missing

**Acceptance**: `python -c "import openai, dotenv"` runs without error after
`pip install -r requirements.txt`.

---

### T2 — Data Models (Priority: P1, Effort: S)

**Goal**: Define all typed dataclasses used throughout the prototype.

**File**: `src/agent/models.py`

**Entities** (see `data-model.md` for full detail):
- `Channel` — enum: `email`, `whatsapp`, `web_form`
- `TicketMessage` — raw inbound message with channel metadata
- `NormalizedTicket` — channel-agnostic internal representation
- `KBResult` — a single knowledge base search result
- `EscalationDecision` — `should_escalate: bool`, `reason: str`, `urgency: str`
- `AgentResponse` — final output: raw text + formatted text + escalation + metadata

**Acceptance**: All classes are importable; repr works on each; no external deps.

---

### T3 — Message Normalization (Priority: P1, Effort: S)

**Goal**: Convert a raw `TicketMessage` (any channel) into a `NormalizedTicket`.

**File**: `src/agent/prototype.py` (function `normalize_message`)

**Rules per channel**:
- `email`: subject field available; formal; no length limit applied at this step
- `whatsapp`: no subject → infer topic from first 10 words of message; phone as identifier
- `web_form`: subject and category pre-filled by form; semi-formal

**Acceptance**:
- Given a `TicketMessage` with `channel=whatsapp` and no subject, `normalize_message`
  infers a topic string from the message text and sets `identifier_type="phone"`.
- Given a `TicketMessage` with `channel=email`, `identifier_type="email"` is preserved.
- `channel` field in the normalized ticket always equals source `channel` value.

---

### T4 — Knowledge Base Search (Priority: P1, Effort: S)

**Goal**: Simple text-search over `context/product-docs.md` to retrieve relevant sections.

**File**: `src/agent/knowledge_base.py`

**Approach** (simple, prototype-appropriate):
1. Load `product-docs.md` and split into sections by `##` headers.
2. For each query, score sections by word overlap (bag-of-words intersection / union).
3. Return top N sections as `KBResult` list sorted by score descending.

No vector embeddings in prototype (those come in production with pgvector).

**Acceptance**:
- Query "Slack integration authentication failed" returns the Slack section (Section 3.1)
  as the top result with a non-zero relevance score.
- Query "xyznonexistentterm999" returns an empty list or results with score < 0.05.
- Loads correctly from both absolute and relative paths.

---

### T5 — Channel Formatter (Priority: P1, Effort: S)

**Goal**: Apply channel-specific formatting rules to a raw AI response string.

**File**: `src/agent/channel_formatter.py`

**Rules** (from constitution Principle III-4 + brand-voice.md):

| Channel | Greeting | Closing | Max chars | Transform |
|---------|----------|---------|-----------|-----------|
| email | "Dear [Name]," | NexaFlow signature block | 2500 (500 words) | No truncation; keep headers |
| whatsapp | "Hi [Name]! 👋" | "Let me know if that helps!" | 1600 hard / 300 soft | Truncate + add "..." if over soft limit |
| web_form | "Hi [Name]," | "Our team is here if you need more help." | 5000 (1000 chars display) | Semi-formal restructure |

**Acceptance**:
- `format_response("Hi Sarah...\n\n[full text]", channel=whatsapp, name="Sarah")`
  returns a string ≤ 1600 chars.
- `format_response(text, channel=email, name="James")` starts with "Dear James,"
  and ends with the NexaFlow signature block.
- `format_response(text, channel=web_form, name="Marcus")` starts with "Hi Marcus,".

---

### T6 — Escalation Evaluator via LLM Intent (Priority: P1, Effort: M)

**Goal**: Use a separate, lightweight LLM call to determine if a ticket requires escalation.

**File**: `src/agent/escalation_evaluator.py`

**Design** (key lesson from Phase 2A — keyword matching causes false positives):
1. Send a focused system prompt to `gpt-4o-mini` asking: "Does this customer message
   require immediate human escalation? Respond ONLY with valid JSON."
2. Expected JSON output: `{"should_escalate": bool, "reason": str, "urgency": "low|normal|high"}`
3. Escalation triggers embedded in the evaluator prompt (8 triggers from constitution V):
   sentiment < 0.3, refund, legal/GDPR, pricing negotiation, 3+ follow-ups, human request,
   data breach, Enterprise SLA breach risk.
4. Do NOT pass keyword lists to the LLM — describe the intent of each trigger conceptually.

**Acceptance**:
- Input: TKT-006 message ("absolutely furious", "dispute the charge", "speak to a manager")
  → `should_escalate=True`, reason mentions sentiment/human-request.
- Input: TKT-003 message ("Will I be charged prorated?")
  → `should_escalate=False` (billing question, not refund request).
- Input: TKT-044 message (GDPR/DPA question)
  → `should_escalate=True`, reason mentions legal/compliance.
- Response is valid JSON parseable with `json.loads()`.

---

### T7 — System Prompt with PKT Datetime Injection (Priority: P1, Effort: S)

**Goal**: Inject current PKT datetime into every agent system prompt.

**File**: `src/agent/prompts.py`

**Implementation**:
```python
from datetime import datetime
from zoneinfo import ZoneInfo

def get_system_prompt(channel: str, customer_name: str) -> str:
    current_dt = datetime.now(ZoneInfo("Asia/Karachi"))
    dt_str = current_dt.strftime("%A, %B %d, %Y at %I:%M %p PKT")
    return f"""You are NexaFlow's AI Customer Success agent.
Current date and time: {dt_str}
Channel: {channel}
Customer: {customer_name}
...
"""
```

**Non-negotiable**: Every prompt generation function MUST call `datetime.now(ZoneInfo(...))`.
No hardcoded dates. No `datetime.utcnow()` for PKT display.

**Acceptance**:
- `get_system_prompt("email", "Sarah")` contains the current date as a string.
- Running the function twice 1 second apart produces strings with the same minute
  (confirming live injection, not cached).

---

### T8 — Core Agent Loop (Priority: P1, Effort: M)

**Goal**: Tie all components into a single `process_ticket()` function.

**File**: `src/agent/prototype.py`

**Flow** (strict order, per constitution Principle IV):
```
1. create_ticket(message)       → ticket_id, normalized_ticket
2. get_customer_history()       → empty list (prototype: no DB)
3. search_knowledge_base(query) → kb_results
4. evaluate_escalation(message) → EscalationDecision
5. IF should_escalate:
     return escalation_response(channel, name, reason)
6. ELSE:
     generate_response(system_prompt, message, kb_results) → raw_response
     format_response(raw_response, channel, name)          → formatted_response
     return AgentResponse(...)
```

**Acceptance**:
- `process_ticket(ticket_message)` returns an `AgentResponse` for all 3 channels.
- Tool call order is `create_ticket` first, `evaluate_escalation` before `generate_response`.
- Escalation path never calls `generate_response` (short-circuits cleanly).
- `AgentResponse.formatted_response` length respects channel limits.

---

### T9 — CLI Entry Point & Prototype Verification (Priority: P2, Effort: S)

**Goal**: Make the prototype runnable from the command line and verify it against
5 representative tickets from Phase 2A.

**File**: `src/agent/prototype.py` (`if __name__ == "__main__":` block)
**Test file**: `tests/test_prototype.py`

**Test tickets** (selected from sample-tickets.json):
- TKT-002 (email, how-to question, neutral) → expect: resolved, no escalation
- TKT-006 (email, furious customer, explicit human request) → expect: escalation
- TKT-025 (whatsapp, short message, neutral) → expect: resolved, short response ≤300 chars
- TKT-032 (whatsapp, gibberish) → expect: clarification request, no escalation
- TKT-044 (web_form, GDPR question) → expect: escalation, legal reason

**Acceptance**:
- All 5 test tickets produce an `AgentResponse` without raising exceptions.
- Test outputs for TKT-006 and TKT-044 have `escalation.should_escalate=True`.
- TKT-025 formatted response is ≤ 1600 chars.
- TKT-002 and TKT-025 (non-escalation) have `escalation.should_escalate=False`.

---

## Complexity Tracking

No constitution violations. All complexity is justified by the incubation phase scope
defined in constitution §8 (Incubation Phase Contract). Production deviations are
explicitly tracked:

| Prototype Simplification | Production Replacement |
|--------------------------|----------------------|
| In-memory ticket creation | PostgreSQL `tickets` table |
| Empty customer history | `get_customer_history` tool + DB query |
| Text search over product-docs.md | pgvector semantic search on `knowledge_base` table |
| Direct `openai.chat.completions` | OpenAI Agents SDK `@function_tool` wrappers |
| Stateless (no Kafka) | Kafka `fte.tickets.incoming` topic |
| Single process | Kubernetes worker pods with HPA |
