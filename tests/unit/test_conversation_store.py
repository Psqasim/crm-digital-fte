"""
Unit tests for ConversationStore (Phase 2C — Memory & State).
Each test uses a fresh ConversationStore() instance — NOT the singleton.
"""
from __future__ import annotations

import uuid

from src.agent.conversation_store import (
    MESSAGE_CAP,
    SENTIMENT_WINDOW,
    URGENCY_SCORE_MAP,
    ConversationStore,
    Message,
)
from src.agent.models import SentimentLabel, TicketStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_store() -> ConversationStore:
    return ConversationStore()


def _make_msg(text: str, direction: str = "inbound", score: float | None = None) -> Message:
    return Message(
        id=f"msg-{uuid.uuid4().hex[:8]}",
        text=text,
        channel="email",
        direction=direction,
        timestamp="2026-04-02T10:00:00+00:00",
        sentiment_score=score,
    )


# ---------------------------------------------------------------------------
# T002 — placeholder (no longer needed but kept for history)
# ---------------------------------------------------------------------------

def test_placeholder():
    pass


# ---------------------------------------------------------------------------
# T007 — US1: get_or_create_customer
# ---------------------------------------------------------------------------

def test_get_or_create_customer_creates_on_first_call():
    store = make_store()
    customer = store.get_or_create_customer("alice@ex.com", "Alice", "email")
    assert customer.email == "alice@ex.com"
    assert customer.name == "Alice"
    assert "email" in customer.channels_used


def test_get_or_create_customer_returns_same_on_second_call():
    store = make_store()
    c1 = store.get_or_create_customer("alice@ex.com", "Alice", "email")
    c2 = store.get_or_create_customer("alice@ex.com", "Alice", "whatsapp")
    assert c1 is c2
    assert "email" in c2.channels_used
    assert "whatsapp" in c2.channels_used


# ---------------------------------------------------------------------------
# T008 — US1: get_or_create_conversation
# ---------------------------------------------------------------------------

def test_get_or_create_conversation_creates_new_for_new_customer():
    store = make_store()
    store.get_or_create_customer("alice@ex.com", "Alice", "email")
    conv = store.get_or_create_conversation("alice@ex.com", "email")
    assert conv.ticket.status == TicketStatus.OPEN
    customer = store.get_customer("alice@ex.com")
    assert conv.id in customer.conversation_ids


# ---------------------------------------------------------------------------
# T009 — US1: add_message 20-cap
# ---------------------------------------------------------------------------

def test_add_message_cap_enforced_at_20():
    store = make_store()
    store.get_or_create_customer("alice@ex.com", "Alice", "email")
    conv = store.get_or_create_conversation("alice@ex.com", "email")
    for i in range(21):
        store.add_message(conv.id, _make_msg(f"msg {i}"))
    assert len(conv.messages) == 20
    assert conv.messages[0].text == "msg 1"  # msg 0 was dropped


# ---------------------------------------------------------------------------
# T010 — US1: get_conversation_context formatting
# ---------------------------------------------------------------------------

def test_get_conversation_context_returns_formatted_string():
    store = make_store()
    store.get_or_create_customer("alice@ex.com", "Alice", "email")
    conv = store.get_or_create_conversation("alice@ex.com", "email")
    store.add_message(conv.id, _make_msg("Hello, I need help", "inbound"))
    store.add_message(conv.id, _make_msg("Sure, let me assist you", "outbound"))
    ctx = store.get_conversation_context("alice@ex.com")
    assert "[INBOUND" in ctx
    assert "[OUTBOUND" in ctx


def test_get_conversation_context_empty_when_no_active():
    store = make_store()
    store.get_or_create_customer("alice@ex.com", "Alice", "email")
    # No conversation created
    ctx = store.get_conversation_context("alice@ex.com")
    assert ctx == ""


# ---------------------------------------------------------------------------
# T017 — US2: resolve_identity
# ---------------------------------------------------------------------------

def test_resolve_identity_email_only():
    store = make_store()
    key = store.resolve_identity(email="alice@ex.com", phone=None)
    assert key == "alice@ex.com"


def test_resolve_identity_phone_only_unmapped():
    store = make_store()
    key = store.resolve_identity(email=None, phone="+923001234567")
    assert key == "phone:+923001234567"


def test_resolve_identity_both_returns_email():
    store = make_store()
    key = store.resolve_identity(email="alice@ex.com", phone="+923001234567")
    assert key == "alice@ex.com"
    # Phone mapping should be created
    assert store._phone_to_email.get("+923001234567") == "alice@ex.com"


# ---------------------------------------------------------------------------
# T018 — US2: link_phone_to_email
# ---------------------------------------------------------------------------

def test_link_phone_creates_mapping():
    store = make_store()
    store.link_phone_to_email("+923001234567", "alice@ex.com")
    key = store.resolve_identity(email=None, phone="+923001234567")
    assert key == "alice@ex.com"


def test_link_phone_to_email_merges_transient_profile():
    store = make_store()
    # Create transient customer via phone-only
    phone = "+923001234567"
    transient_key = f"phone:{phone}"
    store.get_or_create_customer(transient_key, "Alice", "whatsapp")
    conv = store.get_or_create_conversation(transient_key, "whatsapp")
    transient_conv_id = conv.id

    # Now link phone to email
    store.link_phone_to_email(phone, "alice@ex.com")

    # Transient key should be gone
    assert store.get_customer(transient_key) is None

    # Email-keyed profile should have the conversation
    email_customer = store.get_customer("alice@ex.com")
    assert email_customer is not None
    assert transient_conv_id in email_customer.conversation_ids


# ---------------------------------------------------------------------------
# T019 — US2: cross-channel history continuity
# ---------------------------------------------------------------------------

def test_cross_channel_history_continuity():
    store = make_store()
    phone = "+923001234567"
    email = "marcus@ex.com"

    # Step 1: Email message first
    store.get_or_create_customer(email, "Marcus", "email")
    conv_email = store.get_or_create_conversation(email, "email")
    store.add_message(conv_email.id, _make_msg("Email message", "inbound"))

    # Step 2: Link phone → same email
    store.link_phone_to_email(phone, email)

    # Step 3: WhatsApp follow-up should land in same conversation
    customer_key = store.resolve_identity(email=None, phone=phone)
    assert customer_key == email
    conv_wa = store.get_or_create_conversation(customer_key, "whatsapp")
    store.add_message(conv_wa.id, _make_msg("WhatsApp message", "inbound"))

    # Both messages in same conversation
    assert conv_email.id == conv_wa.id
    assert len(conv_wa.messages) == 2


# ---------------------------------------------------------------------------
# T023 — US3: compute_sentiment_trend DETERIORATING
# ---------------------------------------------------------------------------

def test_compute_sentiment_trend_deteriorating():
    store = make_store()
    store.get_or_create_customer("alice@ex.com", "Alice", "email")
    conv = store.get_or_create_conversation("alice@ex.com", "email")
    for score in [0.80, 0.25, 0.05]:
        store.add_message(conv.id, _make_msg("msg", "inbound", score))
    trend = store.compute_sentiment_trend(conv)
    assert trend.label == SentimentLabel.DETERIORATING


def test_compute_sentiment_trend_improving():
    store = make_store()
    store.get_or_create_customer("alice@ex.com", "Alice", "email")
    conv = store.get_or_create_conversation("alice@ex.com", "email")
    for score in [0.40, 0.70, 0.90]:
        store.add_message(conv.id, _make_msg("msg", "inbound", score))
    trend = store.compute_sentiment_trend(conv)
    assert trend.label == SentimentLabel.IMPROVING


# ---------------------------------------------------------------------------
# T024 — US3: stable / insufficient data
# ---------------------------------------------------------------------------

def test_compute_sentiment_trend_stable_insufficient_data():
    store = make_store()
    store.get_or_create_customer("alice@ex.com", "Alice", "email")
    conv = store.get_or_create_conversation("alice@ex.com", "email")
    # Only one scored inbound message
    store.add_message(conv.id, _make_msg("msg", "inbound", 0.10))
    trend = store.compute_sentiment_trend(conv)
    assert trend.label == SentimentLabel.STABLE
    assert trend.window_scores == []


def test_compute_sentiment_trend_stable_mixed():
    store = make_store()
    store.get_or_create_customer("alice@ex.com", "Alice", "email")
    conv = store.get_or_create_conversation("alice@ex.com", "email")
    # Mixed — mean ~0.5, slope ~0 → STABLE
    for score in [0.50, 0.45, 0.55]:
        store.add_message(conv.id, _make_msg("msg", "inbound", score))
    trend = store.compute_sentiment_trend(conv)
    assert trend.label == SentimentLabel.STABLE


# ---------------------------------------------------------------------------
# T025 — US3: sentiment recovery resets trend
# ---------------------------------------------------------------------------

def test_sentiment_recovery_resets_trend():
    store = make_store()
    store.get_or_create_customer("alice@ex.com", "Alice", "email")
    conv = store.get_or_create_conversation("alice@ex.com", "email")
    # Three deteriorating
    for score in [0.80, 0.25, 0.05]:
        store.add_message(conv.id, _make_msg("msg", "inbound", score))
    assert store.compute_sentiment_trend(conv).label == SentimentLabel.DETERIORATING
    # Recovery message — window now [0.25, 0.05, 0.90], mean=0.4, slope=0.65
    store.add_message(conv.id, _make_msg("better", "inbound", 0.90))
    trend = store.compute_sentiment_trend(conv)
    assert trend.label != SentimentLabel.DETERIORATING


# ---------------------------------------------------------------------------
# T028 — US4: valid ticket transitions
# ---------------------------------------------------------------------------

def test_ticket_transition_open_to_pending():
    store = make_store()
    store.get_or_create_customer("alice@ex.com", "Alice", "email")
    conv = store.get_or_create_conversation("alice@ex.com", "email")
    store.transition_ticket(conv.id, TicketStatus.PENDING)
    assert conv.ticket.status == TicketStatus.PENDING


def test_ticket_transition_open_to_escalated():
    store = make_store()
    store.get_or_create_customer("alice@ex.com", "Alice", "email")
    conv = store.get_or_create_conversation("alice@ex.com", "email")
    store.transition_ticket(conv.id, TicketStatus.ESCALATED)
    assert conv.ticket.status == TicketStatus.ESCALATED
    assert conv.ticket.closed_at is not None


def test_ticket_transition_pending_to_resolved():
    store = make_store()
    store.get_or_create_customer("alice@ex.com", "Alice", "email")
    conv = store.get_or_create_conversation("alice@ex.com", "email")
    store.transition_ticket(conv.id, TicketStatus.PENDING)
    store.transition_ticket(conv.id, TicketStatus.RESOLVED)
    assert conv.ticket.status == TicketStatus.RESOLVED
    assert conv.ticket.closed_at is not None


def test_ticket_transition_pending_to_escalated():
    store = make_store()
    store.get_or_create_customer("alice@ex.com", "Alice", "email")
    conv = store.get_or_create_conversation("alice@ex.com", "email")
    store.transition_ticket(conv.id, TicketStatus.PENDING)
    store.transition_ticket(conv.id, TicketStatus.ESCALATED)
    assert conv.ticket.status == TicketStatus.ESCALATED


# ---------------------------------------------------------------------------
# T029 — US4: invalid ticket transitions raise ValueError
# ---------------------------------------------------------------------------

def test_ticket_transition_resolved_raises():
    import pytest
    store = make_store()
    store.get_or_create_customer("alice@ex.com", "Alice", "email")
    conv = store.get_or_create_conversation("alice@ex.com", "email")
    store.transition_ticket(conv.id, TicketStatus.PENDING)
    store.transition_ticket(conv.id, TicketStatus.RESOLVED)
    with pytest.raises(ValueError):
        store.transition_ticket(conv.id, TicketStatus.OPEN)


def test_ticket_transition_escalated_raises():
    import pytest
    store = make_store()
    store.get_or_create_customer("alice@ex.com", "Alice", "email")
    conv = store.get_or_create_conversation("alice@ex.com", "email")
    store.transition_ticket(conv.id, TicketStatus.ESCALATED)
    with pytest.raises(ValueError):
        store.transition_ticket(conv.id, TicketStatus.PENDING)


def test_ticket_transition_pending_to_open_raises():
    import pytest
    store = make_store()
    store.get_or_create_customer("alice@ex.com", "Alice", "email")
    conv = store.get_or_create_conversation("alice@ex.com", "email")
    store.transition_ticket(conv.id, TicketStatus.PENDING)
    with pytest.raises(ValueError):
        store.transition_ticket(conv.id, TicketStatus.OPEN)


# ---------------------------------------------------------------------------
# T030 — US4: resolved ticket creates new conversation
# ---------------------------------------------------------------------------

def test_resolved_ticket_creates_new_conversation():
    store = make_store()
    store.get_or_create_customer("alice@ex.com", "Alice", "email")
    conv1 = store.get_or_create_conversation("alice@ex.com", "email")
    store.transition_ticket(conv1.id, TicketStatus.PENDING)
    store.transition_ticket(conv1.id, TicketStatus.RESOLVED)
    conv2 = store.get_or_create_conversation("alice@ex.com", "email")
    assert conv1.id != conv2.id
    assert conv2.ticket.status == TicketStatus.OPEN


# ---------------------------------------------------------------------------
# T034 — US5: add_topic dedup within conversation
# ---------------------------------------------------------------------------

def test_add_topic_dedup_within_conversation():
    store = make_store()
    store.get_or_create_customer("alice@ex.com", "Alice", "email")
    conv = store.get_or_create_conversation("alice@ex.com", "email")
    store.add_topic(conv.id, "billing")
    store.add_topic(conv.id, "billing")
    assert conv.ticket.topics.count("billing") == 1
    customer = store.get_customer("alice@ex.com")
    assert customer.topic_history["billing"].count(conv.id) == 1


# ---------------------------------------------------------------------------
# T035 — US5: has_prior_topic
# ---------------------------------------------------------------------------

def test_has_prior_topic_true_and_false():
    store = make_store()
    store.get_or_create_customer("alice@ex.com", "Alice", "email")
    conv = store.get_or_create_conversation("alice@ex.com", "email")
    store.add_topic(conv.id, "billing")
    assert store.has_prior_topic("alice@ex.com", "billing") is True
    assert store.has_prior_topic("alice@ex.com", "workflow") is False


# ---------------------------------------------------------------------------
# T036 — US5: count_topic_contacts across sessions
# ---------------------------------------------------------------------------

def test_count_topic_contacts_across_sessions():
    store = make_store()
    store.get_or_create_customer("alice@ex.com", "Alice", "email")

    # Session A
    conv_a = store.get_or_create_conversation("alice@ex.com", "email")
    store.add_topic(conv_a.id, "billing-dispute")
    store.transition_ticket(conv_a.id, TicketStatus.PENDING)
    store.transition_ticket(conv_a.id, TicketStatus.RESOLVED)

    # Session B
    conv_b = store.get_or_create_conversation("alice@ex.com", "email")
    store.add_topic(conv_b.id, "billing-dispute")

    assert store.count_topic_contacts("alice@ex.com", "billing-dispute") == 2


# ---------------------------------------------------------------------------
# T039 — FR-011: no cross-customer data leakage
# ---------------------------------------------------------------------------

def test_no_cross_customer_data_leakage():
    store = make_store()

    # Alice
    store.get_or_create_customer("alice@ex.com", "Alice", "email")
    conv_a = store.get_or_create_conversation("alice@ex.com", "email")
    store.add_message(conv_a.id, _make_msg("Alice private message", "inbound"))

    # Bob
    store.get_or_create_customer("bob@ex.com", "Bob", "email")
    conv_b = store.get_or_create_conversation("bob@ex.com", "email")
    store.add_message(conv_b.id, _make_msg("Bob private message", "inbound"))

    # Alice's context should not contain Bob's data
    alice_ctx = store.get_conversation_context("alice@ex.com")
    assert "Bob private message" not in alice_ctx
    assert "Alice private message" in alice_ctx

    # Bob's profile should not overlap with Alice
    alice_profile = store.get_customer("alice@ex.com")
    bob_profile = store.get_customer("bob@ex.com")
    assert not set(alice_profile.conversation_ids) & set(bob_profile.conversation_ids)

    # Wrong key returns None
    assert store.get_customer("nobody@ex.com") is None


# ---------------------------------------------------------------------------
# T040 — URGENCY_SCORE_MAP values
# ---------------------------------------------------------------------------

def test_sentiment_score_proxy_all_urgency_levels():
    assert URGENCY_SCORE_MAP[("high", True)] == 0.05
    assert URGENCY_SCORE_MAP[("normal", True)] == 0.25
    assert URGENCY_SCORE_MAP[("low", True)] == 0.45
    assert URGENCY_SCORE_MAP[(None, False)] == 0.80
