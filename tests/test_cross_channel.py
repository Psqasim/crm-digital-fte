"""
Cross-channel identity resolution tests.
Covers Marcus Thompson case: TKT-025 (WhatsApp) + TKT-050 (web_form).
"""
from __future__ import annotations

import uuid

from src.agent.conversation_store import ConversationStore, Message
from src.agent.models import TicketStatus


def make_store() -> ConversationStore:
    return ConversationStore()


def _make_msg(text: str, direction: str = "inbound", channel: str = "email") -> Message:
    return Message(
        id=f"msg-{uuid.uuid4().hex[:8]}",
        text=text,
        channel=channel,
        direction=direction,
        timestamp="2026-04-02T10:00:00+00:00",
        sentiment_score=None,
    )


# ---------------------------------------------------------------------------
# Marcus Thompson scenario
# TKT-025: WhatsApp-only (phone +923001234567)
# TKT-050: web_form with email marcus.thompson@techcorp.com
# ---------------------------------------------------------------------------

MARCUS_PHONE = "+923001234567"
MARCUS_EMAIL = "marcus.thompson@techcorp.com"


def test_marcus_phone_only_creates_transient_profile():
    """WhatsApp message with phone only creates transient phone: key."""
    store = make_store()
    key = store.resolve_identity(email=None, phone=MARCUS_PHONE)
    assert key == f"phone:{MARCUS_PHONE}"
    customer = store.get_or_create_customer(key, "Marcus Thompson", "whatsapp")
    assert customer.email == f"phone:{MARCUS_PHONE}"


def test_marcus_web_form_links_phone_to_email():
    """Web form with email links phone → email and merges transient profile."""
    store = make_store()
    phone_key = f"phone:{MARCUS_PHONE}"

    # Step 1: WhatsApp ticket creates transient profile
    store.get_or_create_customer(phone_key, "Marcus Thompson", "whatsapp")
    conv_wa = store.get_or_create_conversation(phone_key, "whatsapp")
    store.add_message(conv_wa.id, _make_msg("My workflow is broken", "inbound", "whatsapp"))

    # Step 2: Web form arrives with email — link phone to email
    store.link_phone_to_email(MARCUS_PHONE, MARCUS_EMAIL)

    # Transient key gone
    assert store.get_customer(phone_key) is None

    # Email-keyed profile exists with WhatsApp conversation
    email_customer = store.get_customer(MARCUS_EMAIL)
    assert email_customer is not None
    assert conv_wa.id in email_customer.conversation_ids


def test_marcus_phone_not_found_returns_none_not_crash():
    """resolve_identity with unknown phone returns transient key, get_customer returns None."""
    store = make_store()
    unknown_phone = "+1999999999"
    key = store.resolve_identity(email=None, phone=unknown_phone)
    assert key == f"phone:{unknown_phone}"
    # No crash — get_customer returns None
    result = store.get_customer(key)
    assert result is None


def test_marcus_same_phone_multiple_emails_uses_most_recent():
    """If phone mapped to one email then re-mapped to another, latest wins."""
    store = make_store()
    phone = MARCUS_PHONE

    # First mapping
    store.link_phone_to_email(phone, "old@ex.com")
    assert store.resolve_identity(email=None, phone=phone) == "old@ex.com"

    # Re-map (most recent)
    store.link_phone_to_email(phone, MARCUS_EMAIL)
    assert store.resolve_identity(email=None, phone=phone) == MARCUS_EMAIL


def test_marcus_unified_history_across_channels():
    """Messages from WhatsApp and web_form appear in same conversation."""
    store = make_store()
    phone_key = f"phone:{MARCUS_PHONE}"

    # WhatsApp session
    store.get_or_create_customer(phone_key, "Marcus Thompson", "whatsapp")
    conv = store.get_or_create_conversation(phone_key, "whatsapp")
    store.add_message(conv.id, _make_msg("TKT-025: workflow broken", "inbound", "whatsapp"))

    # Web form comes in with email — link and re-resolve
    store.link_phone_to_email(MARCUS_PHONE, MARCUS_EMAIL)
    email_key = store.resolve_identity(email=MARCUS_EMAIL, phone=MARCUS_PHONE)
    assert email_key == MARCUS_EMAIL

    # Get active conversation (same one, now under email key)
    store.get_or_create_customer(email_key, "Marcus Thompson", "web_form")
    active = store.get_active_conversation(email_key)
    assert active is not None
    assert active.id == conv.id

    # Web form message goes into same conversation
    store.add_message(active.id, _make_msg("TKT-050: still broken via web", "inbound", "web_form"))

    ctx = store.get_conversation_context(email_key)
    assert "TKT-025" in ctx
    assert "TKT-050" in ctx
