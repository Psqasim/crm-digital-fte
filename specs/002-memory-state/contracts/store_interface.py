"""
ConversationStore — Interface Contract (Phase 2C)
=================================================
This file is a CONTRACT STUB only — not executable code.
It defines the exact public API surface, types, and preconditions
that the implementation in src/agent/conversation_store.py must satisfy.

Do NOT add logic here. Implement in src/agent/conversation_store.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TicketStatus(str, Enum):
    OPEN = "open"
    PENDING = "pending"
    ESCALATED = "escalated"
    RESOLVED = "resolved"


class SentimentLabel(str, Enum):
    IMPROVING = "improving"
    STABLE = "stable"
    DETERIORATING = "deteriorating"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class Message:
    id: str
    text: str
    channel: str                          # Channel enum value ("email"/"whatsapp"/"web_form")
    direction: Literal["inbound", "outbound"]
    timestamp: str                        # ISO-8601 UTC
    sentiment_score: float | None         # 0.0–1.0; None for outbound messages


@dataclass
class Ticket:
    id: str
    conversation_id: str
    status: TicketStatus
    topics: list[str]
    opened_at: str                        # ISO-8601 UTC
    closed_at: str | None = None          # Set when status → resolved or escalated

    def transition(self, new_status: TicketStatus) -> None:
        """
        Allowed transitions:
          open      → pending, escalated
          pending   → resolved, escalated
          resolved  → (raises ValueError — terminal)
          escalated → (raises ValueError — terminal)
        Raises ValueError for any other combination.
        """
        ...  # Implementation in conversation_store.py


@dataclass
class Conversation:
    id: str                               # uuid4 string
    customer_email: str                   # FK → CustomerProfile.email key
    channel_origin: str                   # Channel enum value
    messages: list[Message]               # Max 20; oldest dropped when full
    ticket: Ticket
    created_at: str                       # ISO-8601 UTC
    updated_at: str                       # ISO-8601 UTC


@dataclass
class CustomerProfile:
    email: str                            # Primary key (or "phone:<E164>")
    name: str
    known_phones: set[str]                # E.164 phone numbers
    channels_used: set[str]               # Channel enum values
    topic_history: dict[str, list[str]]   # topic_label → [conversation_id, ...]
    conversation_ids: list[str]           # Ordered oldest → newest
    created_at: str                       # ISO-8601 UTC


@dataclass
class SentimentTrend:
    label: SentimentLabel
    window_scores: list[float]            # Scores used for computation
    window_size: int = 3


# ---------------------------------------------------------------------------
# ConversationStore — public API contract
# ---------------------------------------------------------------------------

class ConversationStore:
    """
    Singleton in-memory store. All state is held in private dicts.
    Thread safety: NOT provided — single-process prototype only.

    Instantiation: use module-level singleton pattern.
      from src.agent.conversation_store import get_store
      store = get_store()
    """

    # ------------------------------------------------------------------
    # Identity resolution
    # ------------------------------------------------------------------

    def resolve_identity(
        self,
        email: str | None,
        phone: str | None,
    ) -> str:
        """
        Returns the canonical customer key.

        Resolution order:
        1. If email provided → return email (also record phone mapping if both given)
        2. If only phone → check _phone_to_email; return mapped email if found
        3. Otherwise → return "phone:<phone>"

        Preconditions: at least one of email/phone must be non-None/non-empty.
        Postcondition: returned key is non-empty string.
        """
        ...

    def link_phone_to_email(self, phone: str, email: str) -> None:
        """
        Creates phone → email mapping.
        If a transient "phone:<phone>" profile exists, merges it into the
        email-keyed profile (topic_history, known_phones, conversation_ids merged).
        The transient profile is deleted after merge.

        Preconditions: phone and email are non-empty strings.
        """
        ...

    # ------------------------------------------------------------------
    # Customer CRUD
    # ------------------------------------------------------------------

    def get_or_create_customer(
        self,
        key: str,
        name: str,
        channel: str,
    ) -> CustomerProfile:
        """
        Returns existing CustomerProfile or creates a new one.
        Updates channels_used with channel on every call.

        Preconditions: key, name non-empty; channel is a valid Channel value.
        """
        ...

    def get_customer(self, key: str) -> CustomerProfile | None:
        """Returns CustomerProfile or None — never raises, never returns another customer's data."""
        ...

    # ------------------------------------------------------------------
    # Conversation management
    # ------------------------------------------------------------------

    def get_or_create_conversation(
        self,
        customer_key: str,
        channel: str,
    ) -> Conversation:
        """
        Returns the active conversation (ticket not resolved/escalated) OR
        creates a new Conversation+Ticket (with status=open).

        'Active' means: most recent conversation whose ticket.status is NOT resolved.
        If most recent ticket is resolved, a new conversation is started.

        Preconditions: customer_key exists in store (call get_or_create_customer first).
        """
        ...

    def get_active_conversation(self, customer_key: str) -> Conversation | None:
        """Returns the active conversation or None if all tickets are resolved/escalated."""
        ...

    # ------------------------------------------------------------------
    # Message management
    # ------------------------------------------------------------------

    def add_message(self, conversation_id: str, message: Message) -> None:
        """
        Appends message to Conversation.messages.
        Enforces 20-message cap: if len == 20 before append, drop messages[0].
        Updates Conversation.updated_at.

        Preconditions: conversation_id exists in store.
        """
        ...

    # ------------------------------------------------------------------
    # Ticket management
    # ------------------------------------------------------------------

    def transition_ticket(
        self,
        conversation_id: str,
        new_status: TicketStatus,
    ) -> None:
        """
        Delegates to Ticket.transition(new_status).
        Sets Ticket.closed_at if new_status is resolved or escalated.

        Raises ValueError on invalid transition.
        Preconditions: conversation_id exists in store.
        """
        ...

    def add_topic(self, conversation_id: str, topic: str) -> None:
        """
        Appends topic to Ticket.topics (if not already present in this conversation).
        Also appends conversation_id to CustomerProfile.topic_history[topic].

        Preconditions: conversation_id exists in store.
        """
        ...

    # ------------------------------------------------------------------
    # Derived / query
    # ------------------------------------------------------------------

    def compute_sentiment_trend(self, conversation: Conversation) -> SentimentTrend:
        """
        Computes trend from last window_size inbound messages with non-None sentiment_score.
        Returns SentimentTrend(label=STABLE, window_scores=[]) if fewer than 2 scored messages.

        Algorithm:
          mean = avg(scores)
          slope = scores[-1] - scores[0]
          DETERIORATING if mean < 0.35 OR (slope < -0.3 AND mean < 0.55)
          IMPROVING     if mean > 0.65 AND slope > 0.2
          STABLE        otherwise
        """
        ...

    def get_conversation_context(self, customer_key: str) -> str:
        """
        Returns a formatted string of the current active conversation history
        suitable for injection into an LLM system prompt.

        Format (each message on its own line):
          [INBOUND | <timestamp>] <text>
          [OUTBOUND | <timestamp>] <text>

        Returns empty string if no active conversation.
        Postcondition: string does NOT contain data from other customers.
        """
        ...

    def has_prior_topic(self, customer_key: str, topic: str) -> bool:
        """Returns True if this customer has ever raised this topic in any prior conversation."""
        ...

    def count_topic_contacts(self, customer_key: str, topic: str) -> int:
        """Returns number of distinct conversations in which this customer raised this topic."""
        ...
