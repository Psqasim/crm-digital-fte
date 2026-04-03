from __future__ import annotations

import re
from dataclasses import dataclass, field, replace

from src.agent.channel_formatter import format_response
from src.agent.conversation_store import get_store
from src.agent.escalation_evaluator import evaluate_escalation
from src.agent.knowledge_base import KnowledgeBase
from src.agent.models import (
    Channel,
    EscalationDecision,
    KBResult,
    SentimentLabel,
    TicketMessage,
)


# ---------------------------------------------------------------------------
# Per-skill result dataclasses
# ---------------------------------------------------------------------------

@dataclass
class CustomerIdentificationResult:
    customer_id: str
    is_returning_customer: bool
    customer_plan: str
    resolution_action: str


@dataclass
class SentimentAnalysisResult:
    sentiment_score: float
    sentiment_label: str
    trend_label: str
    escalation_recommended: bool
    data_points_used: int


@dataclass
class KnowledgeRetrievalResult:
    results: list
    result_count: int


@dataclass
class EscalationDecisionResult:
    should_escalate: bool
    reason: str | None
    urgency: str | None


@dataclass
class ChannelAdaptationResult:
    formatted_response: str
    channel_applied: str
    formatting_notes: list[str]


@dataclass
class InvokerResult:
    customer_id_result: CustomerIdentificationResult
    sentiment_result: SentimentAnalysisResult
    kb_result: KnowledgeRetrievalResult | None
    escalation_result: EscalationDecisionResult
    channel_result: ChannelAdaptationResult | None = None


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _build_formatting_notes(original: str, formatted: str, channel: Channel) -> list[str]:
    """Produce a list of strings describing what changed during formatting."""
    notes: list[str] = []
    orig_sentences = _split_sentences(original)
    fmt_sentences = _split_sentences(formatted)
    if len(fmt_sentences) < len(orig_sentences):
        notes.append(f"truncated to {len(fmt_sentences)} sentences")
    has_sig_original = "NexaFlow Support" in original or "NexaFlow Customer Success" in original
    has_sig_formatted = "NexaFlow Customer Success" in formatted
    if has_sig_original and not has_sig_formatted:
        notes.append("removed signature")
    if not has_sig_original and has_sig_formatted:
        notes.append("added signature")
    if channel == Channel.EMAIL and "Dear" in formatted:
        notes.append("added formal greeting")
    return notes


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences."""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p]


# ---------------------------------------------------------------------------
# SkillsInvoker
# ---------------------------------------------------------------------------

class SkillsInvoker:
    """Orchestrates the 5 agent skills in priority order 0→4."""

    def __init__(self) -> None:
        self._kb = KnowledgeBase()

    # ------------------------------------------------------------------
    # Skill 0 — Customer Identification
    # ------------------------------------------------------------------

    def _run_customer_identification(self, msg: TicketMessage) -> CustomerIdentificationResult:
        store = get_store()

        # Resolve identity
        customer_key = store.resolve_identity(
            email=msg.customer_email,
            phone=msg.customer_phone,
        )

        # T022: Phone-to-email extraction (verbatim from prototype.py:153-162)
        if customer_key.startswith("phone:") and msg.customer_phone:
            extracted_emails = re.findall(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}", msg.message)
            if extracted_emails:
                extracted_email = extracted_emails[0]
                store.link_phone_to_email(msg.customer_phone, extracted_email)
                customer_key = store.resolve_identity(
                    email=extracted_email,
                    phone=msg.customer_phone,
                )

        store.get_or_create_customer(
            key=customer_key,
            name=msg.customer_name,
            channel=msg.channel.value,
        )

        is_returning = len(store.get_conversation_context(customer_key).strip()) > 0

        profile = store.get_customer(customer_key)
        if profile is not None and hasattr(profile, "plan"):
            customer_plan = profile.plan
        else:
            customer_plan = "unknown"

        resolution_action = "matched_existing" if is_returning else "created_new"

        return CustomerIdentificationResult(
            customer_id=customer_key,
            is_returning_customer=is_returning,
            customer_plan=customer_plan,
            resolution_action=resolution_action,
        )

    # ------------------------------------------------------------------
    # Skill 1 — Sentiment Analysis
    # ------------------------------------------------------------------

    def _run_sentiment_analysis(
        self,
        msg: TicketMessage,
        cid: CustomerIdentificationResult,
    ) -> SentimentAnalysisResult:
        store = get_store()
        conversation = store.get_or_create_conversation(
            customer_key=cid.customer_id,
            channel=msg.channel.value,
        )
        trend = store.compute_sentiment_trend(conversation)

        scores = trend.window_scores
        data_points_used = len(scores)

        if data_points_used == 0:
            sentiment_score = 0.0
            sentiment_label = "neutral"
            trend_label = "insufficient_data"
            escalation_recommended = False
        else:
            avg_score = sum(scores) / len(scores)
            sentiment_score = round((avg_score - 0.5) * 2, 4)  # normalise [0,1] → [-1,1]
            if avg_score < 0.4:
                sentiment_label = "negative"
            elif avg_score > 0.65:
                sentiment_label = "positive"
            else:
                sentiment_label = "neutral"

            trend_label = trend.label.value
            escalation_recommended = (
                trend.label == SentimentLabel.DETERIORATING or avg_score < 0.2
            )

        return SentimentAnalysisResult(
            sentiment_score=sentiment_score,
            sentiment_label=sentiment_label,
            trend_label=trend_label,
            escalation_recommended=escalation_recommended,
            data_points_used=data_points_used,
        )

    # ------------------------------------------------------------------
    # Skill 2 — Knowledge Retrieval
    # ------------------------------------------------------------------

    def _run_knowledge_retrieval(self, msg: TicketMessage) -> KnowledgeRetrievalResult:
        # Build query the same way prototype.py:177 does
        # Use message directly since msg here is TicketMessage (not NormalizedTicket)
        query = msg.message[:500]
        try:
            results = self._kb.search(query, top_k=3)
        except Exception:
            results = []
        return KnowledgeRetrievalResult(results=results or [], result_count=len(results or []))

    # ------------------------------------------------------------------
    # Skill 3 — Escalation Decision
    # ------------------------------------------------------------------

    def _run_escalation_decision(
        self,
        msg: TicketMessage,
        sent: SentimentAnalysisResult,
    ) -> EscalationDecisionResult:
        escalation: EscalationDecision = evaluate_escalation(msg.message)

        if escalation.should_escalate:
            return EscalationDecisionResult(
                should_escalate=True,
                reason=escalation.reason,
                urgency=escalation.urgency,
            )
        elif sent.escalation_recommended:
            return EscalationDecisionResult(
                should_escalate=True,
                reason="Deteriorating sentiment trend",
                urgency="high",
            )
        else:
            return EscalationDecisionResult(
                should_escalate=False,
                reason=None,
                urgency=None,
            )

    # ------------------------------------------------------------------
    # Skill 4 — Channel Adaptation
    # ------------------------------------------------------------------

    def apply_channel_adaptation(
        self,
        result: InvokerResult,
        raw_response: str,
        channel: str,
        customer_name: str,
    ) -> InvokerResult:
        if result.escalation_result.should_escalate:
            raise ValueError("apply_channel_adaptation called when should_escalate=True")

        ch = Channel(channel) if isinstance(channel, str) else channel
        formatted = format_response(raw_response, ch, customer_name)
        notes = _build_formatting_notes(raw_response, formatted, ch)

        channel_result = ChannelAdaptationResult(
            formatted_response=formatted,
            channel_applied=ch.value,
            formatting_notes=notes,
        )
        return replace(result, channel_result=channel_result)

    # ------------------------------------------------------------------
    # Pipeline — run() orchestrates skills 0-3
    # ------------------------------------------------------------------

    def run(self, msg: TicketMessage) -> InvokerResult:
        """Execute skills 0-3 sequentially. channel_result=None on return."""
        cid_result = self._run_customer_identification(msg)
        sentiment_result = self._run_sentiment_analysis(msg, cid_result)
        kb_result = self._run_knowledge_retrieval(msg)
        escalation_result = self._run_escalation_decision(msg, sentiment_result)

        return InvokerResult(
            customer_id_result=cid_result,
            sentiment_result=sentiment_result,
            kb_result=kb_result,
            escalation_result=escalation_result,
            channel_result=None,
        )
