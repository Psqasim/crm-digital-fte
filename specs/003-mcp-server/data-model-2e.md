# Data Model: Phase 2E — Agent Skills Structures

**Date**: 2026-04-03
**Branch**: `003-mcp-server`

---

## SkillManifest (src/agent/skills_manifest.py)

Each skill is represented as a `SkillManifest` dataclass instance. Five instances are defined as module-level constants. The registry reads from a `SKILLS` list.

```python
@dataclass(frozen=True)
class SkillManifest:
    skill_id: str          # e.g., "customer_identification_v1"
    name: str              # e.g., "Customer Identification"
    version: str           # e.g., "1.0"
    priority: int          # invocation order: 0 = first, 4 = last
    trigger: str           # natural language description of when to invoke
    connected_tools: list[str]  # module paths or MCP tool names
    guardrails: list[str]       # MUST NOT statements
```

**Instances** (5 total):

| Constant | skill_id | priority |
|----------|----------|----------|
| `CUSTOMER_IDENTIFICATION` | `customer_identification_v1` | 0 |
| `SENTIMENT_ANALYSIS` | `sentiment_analysis_v1` | 1 |
| `KNOWLEDGE_RETRIEVAL` | `knowledge_retrieval_v1` | 2 |
| `ESCALATION_DECISION` | `escalation_decision_v1` | 3 |
| `CHANNEL_ADAPTATION` | `channel_adaptation_v1` | 4 |

---

## SkillResult Types (src/agent/skills_invoker.py)

One result dataclass per skill — typed to match the output schema in the spec manifest.

```python
@dataclass
class CustomerIdentificationResult:
    customer_id: str
    is_returning_customer: bool
    customer_plan: str           # "starter" | "growth" | "enterprise" | "unknown"
    resolution_action: str       # "matched_existing" | "created_new" | "matched_by_cross_channel_link"

@dataclass
class SentimentAnalysisResult:
    sentiment_score: float       # -1.0 to 1.0
    sentiment_label: str         # "positive" | "neutral" | "negative"
    trend_label: str             # "improving" | "stable" | "deteriorating" | "insufficient_data"
    escalation_recommended: bool
    data_points_used: int

@dataclass
class KnowledgeRetrievalResult:
    results: list[KBResult]      # KBResult from knowledge_base.py
    result_count: int

@dataclass
class EscalationDecisionResult:
    should_escalate: bool
    reason: str | None
    urgency: str | None          # "low" | "medium" | "high" | "critical" | None

@dataclass
class ChannelAdaptationResult:
    formatted_response: str
    channel_applied: str
    formatting_notes: list[str]
```

---

## InvokerResult (src/agent/skills_invoker.py)

Aggregates the output of all 5 skills. Returned by `SkillsInvoker.run()`.

```python
@dataclass
class InvokerResult:
    customer_id_result: CustomerIdentificationResult
    sentiment_result: SentimentAnalysisResult
    kb_result: KnowledgeRetrievalResult | None     # None if not a product question
    escalation_result: EscalationDecisionResult
    channel_result: ChannelAdaptationResult | None  # None until after LLM draft
```

**Note**: `kb_result` is `None` when the message is not classified as a product question. `channel_result` is `None` when escalation short-circuits before drafting.

---

## Entity Relationships

```
TicketMessage (input to process_ticket)
       │
       ▼
SkillsInvoker.run(msg)
       │
       ├──► CustomerIdentificationResult  (always)
       ├──► SentimentAnalysisResult       (always)
       ├──► KnowledgeRetrievalResult      (conditional: product question)
       ├──► EscalationDecisionResult      (always)
       └──► ChannelAdaptationResult       (conditional: no escalation)
               │
               ▼
           InvokerResult
               │
               ▼
         process_ticket returns AgentResponse (unchanged output contract)
```

---

## No Schema Changes

Phase 2E adds no new database tables, Kafka topics, or external storage. All new dataclasses are in-memory Python structures within the agent process.
