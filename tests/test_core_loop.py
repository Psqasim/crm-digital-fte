"""
T009 — Test stubs for the core loop (process_ticket).
These tests FAIL before T010 is implemented.
"""
import pytest
from src.agent.models import Channel, TicketMessage


# --- Fixtures ---

def make_tkt_002():
    return TicketMessage(
        id="TKT-002",
        channel=Channel.EMAIL,
        customer_name="James Okonkwo",
        customer_email="james@techvault.io",
        customer_phone=None,
        subject="How do I set up automation for due date reminders?",
        message=(
            "Hello NexaFlow team, I'm trying to create an automation that sends a Slack message "
            "to my team 2 days before a task is due. I found the automation rules section but "
            "I'm not sure how to configure the trigger and action correctly. "
            "Could you walk me through it step by step?"
        ),
        received_at="2026-03-15T09:45:00Z",
        metadata={},
        category=None,
    )


def make_tkt_006():
    return TicketMessage(
        id="TKT-006",
        channel=Channel.EMAIL,
        customer_name="Michael Torres",
        customer_email="michael.torres@nexgen-ops.com",
        customer_phone=None,
        subject="This is completely broken — I'm cancelling if not fixed TODAY",
        message=(
            "I am absolutely furious right now. For the THIRD time this week, all my automation "
            "rules have stopped firing. I have an entire operations team of 12 people whose "
            "workflows depend on this. We missed two critical deadlines because your system failed. "
            "I've already emailed twice this week with no resolution. I demand to speak to a "
            "manager or senior engineer immediately. If this isn't resolved today I am cancelling "
            "our Growth subscription and disputing the charge."
        ),
        received_at="2026-03-15T13:47:58Z",
        metadata={},
        category=None,
    )


def make_tkt_025():
    return TicketMessage(
        id="TKT-025",
        channel=Channel.WHATSAPP,
        customer_name="Marcus Thompson",
        customer_email="marcus.t@buildright.co.uk",
        customer_phone="+447911123456",
        subject=None,
        message="My due date reminders stopped sending to Slack. Was working fine yesterday.",
        received_at="2026-03-15T10:30:00Z",
        metadata={"wa_id": "447911123456"},
        category=None,
    )


# --- Tests ---

def test_process_ticket_returns_agent_response_for_email():
    """process_ticket(TKT-002 email) returns AgentResponse without exception."""
    from src.agent.prototype import process_ticket
    from src.agent.models import AgentResponse

    result = process_ticket(make_tkt_002())

    assert isinstance(result, AgentResponse), f"Expected AgentResponse, got {type(result)}"


def test_escalation_always_populated():
    """AgentResponse.escalation is never null — it is evaluated for every ticket."""
    from src.agent.prototype import process_ticket

    result = process_ticket(make_tkt_002())

    assert result.escalation is not None, "escalation field must always be populated"
    assert result.escalation.should_escalate is not None


def test_tkt006_escalates_without_llm_response():
    """TKT-006 → should_escalate=True; escalated ticket short-circuits LLM generation."""
    from src.agent.prototype import process_ticket

    result = process_ticket(make_tkt_006())

    assert result.escalation.should_escalate is True, (
        f"TKT-006 should escalate; reason: {result.escalation.reason!r}"
    )
    assert result.kb_results_used == [], (
        "Escalated tickets must have empty kb_results_used (short-circuit path)"
    )


def test_tkt025_whatsapp_response_length():
    """TKT-025 (WhatsApp) → formatted_response length ≤ 1600 chars."""
    from src.agent.prototype import process_ticket

    result = process_ticket(make_tkt_025())

    assert result.formatted_response, "formatted_response must not be empty"
    assert len(result.formatted_response) <= 1600, (
        f"WhatsApp response too long: {len(result.formatted_response)} chars"
    )
