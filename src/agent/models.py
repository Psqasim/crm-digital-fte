from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Channel(str, Enum):
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    WEB_FORM = "web_form"


@dataclass
class TicketMessage:
    id: str
    channel: Channel
    customer_name: str
    customer_email: str | None
    customer_phone: str | None
    subject: str | None
    message: str
    received_at: str
    metadata: dict
    category: str | None = None


@dataclass
class NormalizedTicket:
    ticket_id: str
    channel: Channel
    customer_name: str
    customer_first_name: str
    customer_email: str | None
    customer_phone: str | None
    identifier_type: str
    inferred_topic: str
    message: str
    message_word_count: int
    category_hint: str | None
    received_at: str
    source_metadata: dict
    language_hint: str


@dataclass
class KBResult:
    section_title: str
    content: str
    relevance_score: float


@dataclass
class EscalationDecision:
    should_escalate: bool
    reason: str
    urgency: str
    raw_llm_response: str


class TicketStatus(str, Enum):
    OPEN = "open"
    PENDING = "pending"
    ESCALATED = "escalated"
    RESOLVED = "resolved"


class SentimentLabel(str, Enum):
    IMPROVING = "improving"
    STABLE = "stable"
    DETERIORATING = "deteriorating"


@dataclass
class SentimentTrend:
    label: SentimentLabel
    window_scores: list[float]
    window_size: int = 3


@dataclass
class AgentResponse:
    ticket_id: str
    channel: Channel
    raw_response: str
    formatted_response: str
    escalation: EscalationDecision
    kb_results_used: list[KBResult]
    processing_time_ms: float
    model_used: str
    prompt_datetime: str
