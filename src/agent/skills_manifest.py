from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SkillManifest:
    skill_id: str
    name: str
    version: str
    priority: int          # 0 = first, 4 = last
    trigger: str
    connected_tools: list[str] = field(default_factory=list)
    guardrails: list[str] = field(default_factory=list)


CUSTOMER_IDENTIFICATION = SkillManifest(
    skill_id="customer_identification_v1",
    name="Customer Identification",
    version="1.0",
    priority=0,
    trigger=(
        "Invoke as the FIRST step on every incoming message, before any other skill. "
        "No downstream skill may run until a customer_id is resolved."
    ),
    connected_tools=[
        "src/agent/conversation_store.py::ConversationStore",
        "src/agent/models.py",
    ],
    guardrails=[
        "MUST NOT proceed without resolving at least a temporary customer_id — even for anonymous sessions.",
        "MUST NOT merge two customer profiles without at least one shared identifier (email or phone).",
        "MUST NOT expose PII (raw email or phone) in the output — output only customer_id.",
        "MUST create a new profile (is_returning_customer: false) rather than failing when no match is found.",
        "MUST be idempotent — calling with the same raw_message_id twice must return the same customer_id.",
    ],
)

SENTIMENT_ANALYSIS = SkillManifest(
    skill_id="sentiment_analysis_v1",
    name="Sentiment Analysis",
    version="1.0",
    priority=1,
    trigger=(
        "Invoke on EVERY incoming customer message, immediately after Customer "
        "Identification resolves the customer_id. Must run before escalation "
        "decision and response generation."
    ),
    connected_tools=[
        "mcp_tool:get_sentiment_trend",
        "src/agent/conversation_store.py::ConversationStore::compute_sentiment_trend",
        "src/agent/escalation_evaluator.py::evaluate_escalation",
    ],
    guardrails=[
        "MUST NOT skip invocation even if message appears clearly positive.",
        "MUST NOT store sentiment scores under a different customer_id than the resolved one.",
        "MUST NOT recommend escalation solely based on one message unless score < -0.8.",
        "MUST return trend_label 'insufficient_data' (not an error) when fewer than 3 prior messages exist.",
    ],
)

KNOWLEDGE_RETRIEVAL = SkillManifest(
    skill_id="knowledge_retrieval_v1",
    name="Knowledge Retrieval",
    version="1.0",
    priority=2,
    trigger=(
        "Invoke when the customer message contains a question about NexaFlow features, "
        "pricing, integrations, plans, or usage. Also invoke when the agent needs "
        "factual product content to compose an accurate reply."
    ),
    connected_tools=[
        "mcp_tool:search_knowledge_base",
        "src/agent/knowledge_base.py::KnowledgeBase::search",
    ],
    guardrails=[
        "MUST NOT invent or synthesize content not present in the knowledge base.",
        "MUST NOT return results from a previous query when the current query returns empty.",
        "MUST NOT expose raw file paths or internal module names in the output.",
        "MUST NOT block if result count is zero — return empty array, not an error.",
    ],
)

ESCALATION_DECISION = SkillManifest(
    skill_id="escalation_decision_v1",
    name="Escalation Decision",
    version="1.0",
    priority=3,
    trigger=(
        "Invoke AFTER the agent has drafted a response but BEFORE sending it. "
        "Also invoke immediately if Sentiment Analysis returns "
        "escalation_recommended: true — in that case, skip drafting entirely."
    ),
    connected_tools=[
        "mcp_tool:escalate_to_human",
        "src/agent/escalation_evaluator.py::evaluate_escalation",
    ],
    guardrails=[
        "MUST NOT escalate based solely on ticket age for Starter-tier customers (they have no SLA).",
        "MUST escalate (should_escalate: true, urgency: critical) when message_text contains explicit threats or profanity trigger words defined in escalation-rules.md.",
        "MUST NOT silently suppress escalation if the escalate_to_human MCP tool is unavailable — surface the error.",
        "MUST NOT change ticket status itself — that is the responsibility of the escalate_to_human MCP tool.",
    ],
)

CHANNEL_ADAPTATION = SkillManifest(
    skill_id="channel_adaptation_v1",
    name="Channel Adaptation",
    version="1.0",
    priority=4,
    trigger=(
        "Invoke on EVERY outbound response, immediately before the send_response "
        "MCP tool is called. No response may be dispatched without passing through "
        "this skill first."
    ),
    connected_tools=[
        "src/agent/channel_formatter.py",
        "mcp_tool:send_response",
    ],
    guardrails=[
        "MUST NOT send the unformatted response_text directly — always apply channel rules.",
        "MUST NOT add a signature block to whatsapp or web_form channels.",
        "MUST NOT exceed 3 sentences for whatsapp channel — truncate with '...' if necessary.",
        "MUST NOT alter factual content during formatting — only structure and style may change.",
        "MUST return the response unchanged (with a warning flag) for an unrecognized channel value, rather than raising an error.",
    ],
)

SKILLS: list[SkillManifest] = [
    CUSTOMER_IDENTIFICATION,
    SENTIMENT_ANALYSIS,
    KNOWLEDGE_RETRIEVAL,
    ESCALATION_DECISION,
    CHANNEL_ADAPTATION,
]
