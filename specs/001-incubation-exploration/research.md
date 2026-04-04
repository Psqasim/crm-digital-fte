# Research: Phase 2B — Prototype Core Loop

**Date**: 2026-04-01
**Feature**: 001-incubation-exploration
**Status**: Complete — all unknowns resolved

---

## Research Item 1: OpenAI API Usage for Prototype

**Decision**: Use `openai` Python SDK v1.x with `client.chat.completions.create()`.
Model `gpt-4o-mini` for escalation evaluator (cheap, fast, structured output);
model `gpt-4o` for main response generation (higher quality).

**Rationale**:
- `gpt-4o-mini` at ~$0.15/1M input tokens is cost-effective for a binary
  escalation classification call (short prompt, short response).
- `gpt-4o` produces higher-quality customer-facing responses — justified for
  the response generation step where quality directly impacts customer experience.
- Using two different models in the same prototype is intentional and demonstrates
  the cost-optimization principle: use the cheapest model that passes the task.

**Alternatives considered**:
- `gpt-3.5-turbo` — deprecated in favour of `gpt-4o-mini`; rejected.
- Raw HTTP requests — unnecessarily low-level; SDK handles retries, timeouts.
- Streaming responses — not needed for prototype; adds complexity without benefit.

**Usage pattern**:
```python
from openai import OpenAI
client = OpenAI()  # reads OPENAI_API_KEY from env

# Escalation call (cheap model, structured output)
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "system", "content": evaluator_prompt},
              {"role": "user", "content": customer_message}],
    response_format={"type": "json_object"},
    max_tokens=150,
    temperature=0.0,
)
result = json.loads(response.choices[0].message.content)
```

---

## Research Item 2: LLM-Intent Escalation (vs. Keyword Matching)

**Decision**: Use a dedicated LLM call for escalation evaluation with a prompt that
describes each escalation trigger conceptually, not as keyword lists. Expect JSON output.

**Rationale** (discovered in Phase 2A):
- Keyword matching produced 3 false positives in 60 tickets (5% FPR):
  - "charged" in TKT-003 triggered refund detection (actual: billing question)
  - "manager" in TKT-042 triggered human-request detection (actual: job title)
  - "manager" in TKT-051 triggered human-request detection (actual: role description)
- LLM intent detection understands context: "Will I be charged prorated?" ≠ "I want a refund"
- JSON response format (`{"should_escalate": bool, "reason": str, "urgency": str}`)
  gives structured output safe to parse without post-processing heuristics.

**Escalation prompt design**: Describe each of the 8 triggers as intent descriptions,
not regex patterns. Example:
- "Customer is expressing extreme anger or frustration (not merely disappointment)"
- "Customer is asking for money back for a charge already made (refund request)"
- vs: NOT "look for the word 'refund'"

**Alternatives considered**:
- Keyword regex matching — rejected; 5% FPR demonstrated in Phase 2A
- Zero-shot binary classification without JSON — rejected; harder to parse
- Fine-tuned classifier — overkill for prototype; revisit in production if needed

---

## Research Item 3: Simple Knowledge Base Search (Text Search)

**Decision**: Load `context/product-docs.md`, split by `##` section headers, score
each section by Jaccard similarity (word-set intersection / union) against query words.
Return top 3 sections with score > 0.05.

**Rationale**:
- Product docs are structured with clear `##` headers (10 sections identified)
- Jaccard similarity is O(n×|sections|) — fast enough for 10 sections
- No external NLP library needed (pure Python sets)
- Prototype-appropriate: simple, transparent, debuggable

**Alternatives considered**:
- TF-IDF (sklearn) — adds dependency; marginal improvement for 10 sections
- pgvector semantic search — this is the production approach (Stage 2);
  intentionally deferred per Complexity Tracking in plan.md
- BM25 (rank-bm25) — good middle ground but adds dependency; not justified for prototype

**Section split logic**:
```python
import re
sections = re.split(r'\n## ', docs_text)
# Each section starts with its title
```

---

## Research Item 4: Channel Formatting Rules

**Decision**: Apply formatting rules from `context/brand-voice.md` (already in repo).
No additional research needed — rules are fully specified.

**Key rules confirmed**:
- Email: `"Dear [FirstName],"` + body + NexaFlow signature block (3 lines)
- WhatsApp: `"Hi [FirstName]! 👋"` + ≤300 char body (soft limit) + natural close
- Web Form: `"Hi [FirstName],"` + numbered steps if multi-step + support link close

**Hard length limits (for truncation)**:
- Email: 2500 chars (≈500 words), no truncation needed — email can be long
- WhatsApp: 1600 chars hard Twilio limit; 300 chars preferred; truncate at word boundary
- Web Form: 5000 chars (no practical limit for prototype)

---

## Research Item 5: PKT Datetime Injection

**Decision**: Use `datetime.now(ZoneInfo("Asia/Karachi"))` as mandated by constitution.
`ZoneInfo` is part of Python 3.9+ standard library — no extra dependency.

**Display format**: `"%A, %B %d, %Y at %I:%M %p PKT"` → e.g., "Tuesday, April 01, 2026 at 04:17 PM PKT"

**Placement in prompt**: First non-agent-name line of the system prompt, so the LLM
sees it at the very beginning of context (highest attention weight position).

**Alternatives considered**:
- `pytz.timezone("Asia/Karachi")` — extra dependency; `zoneinfo` is stdlib since 3.9
- UTC timestamps — rejected per constitution; PKT is required for SLA calculations

---

## Resolution Summary

All NEEDS CLARIFICATION items resolved. No blockers.

| Item | Decision | Confidence |
|------|----------|------------|
| OpenAI model choice | gpt-4o-mini (eval) + gpt-4o (response) | High |
| Escalation detection method | LLM-intent with JSON output | High |
| Knowledge base search | Jaccard text search, no external deps | High |
| Channel formatter rules | Brand voice doc, fully specified | High |
| Datetime injection | ZoneInfo stdlib, PKT format | High |
