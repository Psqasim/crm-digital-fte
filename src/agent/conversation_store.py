"""
conversation_store.py — In-memory ConversationStore for Phase 2C.

Holds all customer profiles, conversations, messages, tickets, and
cross-channel identity mappings. No external persistence — state is
reset on process restart.

See specs/002-memory-state/contracts/store_interface.py for the typed API contract.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

from src.agent.models import SentimentLabel, SentimentTrend, TicketStatus

# ---------------------------------------------------------------------------
# Sentinel constants
# ---------------------------------------------------------------------------

MESSAGE_CAP = 20
SENTIMENT_WINDOW = 3

URGENCY_SCORE_MAP: dict[tuple, float] = {
    ("high", True): 0.05,
    ("normal", True): 0.25,
    ("low", True): 0.45,
    (None, False): 0.80,
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Message:
    id: str
    text: str
    channel: str
    direction: Literal["inbound", "outbound"]
    timestamp: str
    sentiment_score: float | None


@dataclass
class Ticket:
    id: str
    conversation_id: str
    status: TicketStatus
    topics: list[str]
    opened_at: str
    closed_at: str | None = None

    def transition(self, new_status: TicketStatus) -> None:
        allowed = {
            TicketStatus.OPEN: {TicketStatus.PENDING, TicketStatus.ESCALATED},
            TicketStatus.PENDING: {TicketStatus.RESOLVED, TicketStatus.ESCALATED},
            TicketStatus.RESOLVED: set(),
            TicketStatus.ESCALATED: set(),
        }
        if new_status not in allowed[self.status]:
            raise ValueError(f"Invalid transition: {self.status} → {new_status}")
        self.status = new_status


@dataclass
class Conversation:
    id: str
    customer_email: str
    channel_origin: str
    messages: list[Message]
    ticket: Ticket
    created_at: str
    updated_at: str


@dataclass
class CustomerProfile:
    email: str
    name: str
    known_phones: set[str]
    channels_used: set[str]
    topic_history: dict[str, list[str]]
    conversation_ids: list[str]
    created_at: str


# ---------------------------------------------------------------------------
# ConversationStore
# ---------------------------------------------------------------------------

class ConversationStore:
    """
    In-memory store. Thread safety: NOT provided (single-process prototype).
    Use get_store() for the module-level singleton, or instantiate directly in tests.
    """

    def __init__(self) -> None:
        self._customers: dict[str, CustomerProfile] = {}
        self._conversations: dict[str, Conversation] = {}
        self._phone_to_email: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Identity resolution
    # ------------------------------------------------------------------

    def resolve_identity(self, email: str | None, phone: str | None) -> str:
        if email:
            if phone:
                self._phone_to_email[phone] = email
            return email
        if phone:
            if phone in self._phone_to_email:
                return self._phone_to_email[phone]
            return f"phone:{phone}"
        raise ValueError("resolve_identity: at least one of email/phone must be provided")

    def link_phone_to_email(self, phone: str, email: str) -> None:
        self._phone_to_email[phone] = email
        transient_key = f"phone:{phone}"
        if transient_key in self._customers:
            transient = self._customers[transient_key]
            # Ensure email-keyed profile exists
            if email not in self._customers:
                self._customers[email] = CustomerProfile(
                    email=email,
                    name=transient.name,
                    known_phones=set(),
                    channels_used=set(),
                    topic_history={},
                    conversation_ids=[],
                    created_at=_utcnow(),
                )
            target = self._customers[email]
            # Merge data
            target.known_phones.update(transient.known_phones)
            target.known_phones.add(phone)
            target.channels_used.update(transient.channels_used)
            # Merge conversation_ids (avoid duplicates, preserve order)
            for cid in transient.conversation_ids:
                if cid not in target.conversation_ids:
                    target.conversation_ids.append(cid)
                # Update conversation's customer_email FK
                if cid in self._conversations:
                    self._conversations[cid].customer_email = email
            # Merge topic_history
            for topic, conv_ids in transient.topic_history.items():
                if topic not in target.topic_history:
                    target.topic_history[topic] = []
                for cid in conv_ids:
                    if cid not in target.topic_history[topic]:
                        target.topic_history[topic].append(cid)
            del self._customers[transient_key]

    # ------------------------------------------------------------------
    # Customer CRUD
    # ------------------------------------------------------------------

    def get_or_create_customer(self, key: str, name: str, channel: str) -> CustomerProfile:
        if key not in self._customers:
            self._customers[key] = CustomerProfile(
                email=key,
                name=name,
                known_phones=set(),
                channels_used={channel},
                topic_history={},
                conversation_ids=[],
                created_at=_utcnow(),
            )
        else:
            self._customers[key].channels_used.add(channel)
        return self._customers[key]

    def get_customer(self, key: str) -> CustomerProfile | None:
        return self._customers.get(key)

    # ------------------------------------------------------------------
    # Conversation management
    # ------------------------------------------------------------------

    def get_or_create_conversation(self, customer_key: str, channel: str) -> Conversation:
        customer = self._customers[customer_key]
        # Find active conversation
        active = self.get_active_conversation(customer_key)
        if active is not None:
            return active
        # Create new conversation + ticket
        conv_id = str(uuid.uuid4())
        ticket_id = f"TKT-{uuid.uuid4().hex[:8]}"
        now = _utcnow()
        ticket = Ticket(
            id=ticket_id,
            conversation_id=conv_id,
            status=TicketStatus.OPEN,
            topics=[],
            opened_at=now,
            closed_at=None,
        )
        conv = Conversation(
            id=conv_id,
            customer_email=customer_key,
            channel_origin=channel,
            messages=[],
            ticket=ticket,
            created_at=now,
            updated_at=now,
        )
        self._conversations[conv_id] = conv
        customer.conversation_ids.append(conv_id)
        return conv

    def get_active_conversation(self, customer_key: str) -> Conversation | None:
        customer = self._customers.get(customer_key)
        if not customer:
            return None
        # Most recent conversation that is not resolved or escalated
        for conv_id in reversed(customer.conversation_ids):
            conv = self._conversations.get(conv_id)
            if conv and conv.ticket.status not in (TicketStatus.RESOLVED, TicketStatus.ESCALATED):
                return conv
        return None

    # ------------------------------------------------------------------
    # Message management
    # ------------------------------------------------------------------

    def add_message(self, conversation_id: str, message: Message) -> None:
        conv = self._conversations[conversation_id]
        if len(conv.messages) >= MESSAGE_CAP:
            conv.messages.pop(0)
        conv.messages.append(message)
        conv.updated_at = _utcnow()

    # ------------------------------------------------------------------
    # Ticket management
    # ------------------------------------------------------------------

    def transition_ticket(self, conversation_id: str, new_status: TicketStatus) -> None:
        conv = self._conversations[conversation_id]
        conv.ticket.transition(new_status)
        if new_status in (TicketStatus.RESOLVED, TicketStatus.ESCALATED):
            conv.ticket.closed_at = _utcnow()

    def add_topic(self, conversation_id: str, topic: str) -> None:
        conv = self._conversations[conversation_id]
        # Add to ticket topics (dedup within conversation)
        if topic not in conv.ticket.topics:
            conv.ticket.topics.append(topic)
        # Add to customer profile topic_history
        customer = self._customers.get(conv.customer_email)
        if customer is not None:
            if topic not in customer.topic_history:
                customer.topic_history[topic] = []
            if conversation_id not in customer.topic_history[topic]:
                customer.topic_history[topic].append(conversation_id)

    # ------------------------------------------------------------------
    # Derived / query
    # ------------------------------------------------------------------

    def compute_sentiment_trend(self, conversation: Conversation) -> SentimentTrend:
        # Extract last SENTIMENT_WINDOW inbound messages with non-None score
        inbound_scores = [
            m.sentiment_score
            for m in conversation.messages
            if m.direction == "inbound" and m.sentiment_score is not None
        ][-SENTIMENT_WINDOW:]

        if len(inbound_scores) < 2:
            return SentimentTrend(label=SentimentLabel.STABLE, window_scores=[], window_size=SENTIMENT_WINDOW)

        mean = sum(inbound_scores) / len(inbound_scores)
        slope = inbound_scores[-1] - inbound_scores[0]

        if mean < 0.35 or (slope < -0.3 and mean < 0.55):
            label = SentimentLabel.DETERIORATING
        elif mean > 0.65 and slope > 0.2:
            label = SentimentLabel.IMPROVING
        else:
            label = SentimentLabel.STABLE

        return SentimentTrend(label=label, window_scores=inbound_scores, window_size=SENTIMENT_WINDOW)

    def get_conversation_context(self, customer_key: str) -> str:
        conv = self.get_active_conversation(customer_key)
        if not conv:
            return ""
        lines = []
        for m in conv.messages:
            direction = "INBOUND" if m.direction == "inbound" else "OUTBOUND"
            lines.append(f"[{direction} | {m.timestamp}] {m.text}")
        return "\n".join(lines)

    def has_prior_topic(self, customer_key: str, topic: str) -> bool:
        customer = self._customers.get(customer_key)
        if not customer:
            return False
        return len(customer.topic_history.get(topic, [])) > 0

    def count_topic_contacts(self, customer_key: str, topic: str) -> int:
        customer = self._customers.get(customer_key)
        if not customer:
            return 0
        return len(customer.topic_history.get(topic, []))


# ---------------------------------------------------------------------------
# Module-level singleton (ADR-0001 injectable pattern)
# ---------------------------------------------------------------------------

_store: ConversationStore | None = None


def get_store() -> ConversationStore:
    global _store
    if _store is None:
        _store = ConversationStore()
    return _store


def reset_store() -> None:
    """Test helper — resets singleton so next get_store() returns a fresh instance."""
    global _store
    _store = None
