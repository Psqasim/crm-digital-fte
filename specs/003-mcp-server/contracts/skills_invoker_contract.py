"""
Phase 2E — Skills Invoker API Contract

This file defines the typed interface for the SkillsInvoker.
It is a SPECIFICATION CONTRACT — not runnable production code.

Implementors must satisfy every method signature, parameter type,
return type, and docstring constraint listed here.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


# ---------------------------------------------------------------------------
# Input type (passed in from process_ticket)
# ---------------------------------------------------------------------------

class TicketMessageProtocol(Protocol):
    """Subset of TicketMessage fields consumed by the invoker."""
    message: str
    customer_email: str | None
    customer_phone: str | None
    customer_name: str
    customer_first_name: str
    channel: object          # src.agent.models.Channel enum


# ---------------------------------------------------------------------------
# Per-skill result types
# ---------------------------------------------------------------------------

@dataclass
class CustomerIdentificationResult:
    customer_id: str
    """Stable, unified key for this customer (email-prefixed or phone-prefixed)."""
    is_returning_customer: bool
    """True when the customer had prior conversations in the store."""
    customer_plan: str
    """One of: 'starter' | 'growth' | 'enterprise' | 'unknown'."""
    resolution_action: str
    """One of: 'matched_existing' | 'created_new' | 'matched_by_cross_channel_link'."""


@dataclass
class SentimentAnalysisResult:
    sentiment_score: float
    """Range [-1.0, 1.0]. Negative = frustrated, positive = satisfied, 0 = neutral."""
    sentiment_label: str
    """One of: 'positive' | 'neutral' | 'negative'."""
    trend_label: str
    """One of: 'improving' | 'stable' | 'deteriorating' | 'insufficient_data'."""
    escalation_recommended: bool
    """True when trend is deteriorating or score < -0.6."""
    data_points_used: int
    """Number of prior messages used to compute the trend (may be 0)."""


@dataclass
class KnowledgeRetrievalResult:
    results: list
    """List of KBResult objects from KnowledgeBase.search()."""
    result_count: int
    """Length of results; 0 when no match found (never an error)."""


@dataclass
class EscalationDecisionResult:
    should_escalate: bool
    """When True, process_ticket MUST skip LLM generation and route to human."""
    reason: str | None
    """Human-readable explanation; None when should_escalate is False."""
    urgency: str | None
    """One of: 'low' | 'medium' | 'high' | 'critical' | None."""


@dataclass
class ChannelAdaptationResult:
    formatted_response: str
    """The response text after channel-specific formatting is applied."""
    channel_applied: str
    """Echo of the channel used (for logging/debugging)."""
    formatting_notes: list[str]
    """List of transformations applied (e.g., 'truncated to 3 sentences', 'added signature')."""


@dataclass
class InvokerResult:
    customer_id_result: CustomerIdentificationResult
    sentiment_result: SentimentAnalysisResult
    kb_result: KnowledgeRetrievalResult | None
    """None when the message is not classified as a product question."""
    escalation_result: EscalationDecisionResult
    channel_result: ChannelAdaptationResult | None
    """None when escalation short-circuits before channel adaptation."""


# ---------------------------------------------------------------------------
# SkillsInvoker interface
# ---------------------------------------------------------------------------

class SkillsInvokerProtocol(Protocol):
    """
    Orchestrates the 5 agent skills in the mandatory invocation order.

    Priority order (0→4):
      0. Customer Identification  — always first
      1. Sentiment Analysis       — every message
      2. Knowledge Retrieval      — conditional (product question)
      3. Escalation Decision      — after KB; uses sentiment result
      4. Channel Adaptation       — only if no escalation; after LLM draft

    Usage in process_ticket:
        invoker = SkillsInvoker()
        result = invoker.run(msg)
        if result.escalation_result.should_escalate:
            # skip LLM, use escalation acknowledgment template
        else:
            raw_draft = llm_generate(result.kb_result, result.customer_id_result, ...)
            result = invoker.apply_channel_adaptation(result, raw_draft, channel)
    """

    def run(self, msg: TicketMessageProtocol) -> InvokerResult:
        """
        Execute skills 0–3 sequentially. Does NOT call Channel Adaptation (skill 4)
        because channel adaptation requires the LLM draft, which process_ticket
        generates after this method returns.

        Steps:
          1. run_customer_identification(msg) → CustomerIdentificationResult
          2. run_sentiment_analysis(msg, customer_id_result) → SentimentAnalysisResult
          3. run_knowledge_retrieval(msg) → KnowledgeRetrievalResult | None
          4. run_escalation_decision(msg, sentiment_result) → EscalationDecisionResult

        Returns InvokerResult with channel_result=None (to be filled by apply_channel_adaptation).

        Raises: never. All errors are captured as fallback result values per skill guardrails.
        """
        ...

    def apply_channel_adaptation(
        self,
        result: InvokerResult,
        raw_response: str,
        channel: str,
        customer_name: str,
    ) -> InvokerResult:
        """
        Execute skill 4 (Channel Adaptation) after LLM draft is available.
        Returns a new InvokerResult with channel_result populated.

        Precondition: result.escalation_result.should_escalate must be False.
        If called when should_escalate is True, raises ValueError.
        """
        ...


# ---------------------------------------------------------------------------
# SkillsRegistry interface
# ---------------------------------------------------------------------------

class SkillsRegistryProtocol(Protocol):
    """
    Provides lookup for SkillManifest definitions by skill_id.
    Registry is populated at module-import time from SKILLS list constant.
    """

    def get_skill(self, skill_id: str) -> object:
        """
        Return the SkillManifest for the given skill_id.

        Raises KeyError if skill_id is not registered.
        Never returns None — callers should catch KeyError.
        """
        ...

    def list_skills(self) -> list[object]:
        """Return all registered SkillManifest instances ordered by priority (ascending)."""
        ...
