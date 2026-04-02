"""
T011 — Integration tests loading fixtures from context/sample-tickets.json.
Tests TKT-002, TKT-006, TKT-025, TKT-032, TKT-044.
"""
import json
import time
from pathlib import Path

import pytest

from src.agent.models import Channel, TicketMessage

_FIXTURES_PATH = Path(__file__).parent.parent / "context" / "sample-tickets.json"


def _load_ticket(ticket_id: str) -> TicketMessage:
    with open(_FIXTURES_PATH) as f:
        tickets = json.load(f)
    raw = next(t for t in tickets if t["id"] == ticket_id)
    return TicketMessage(
        id=raw["id"],
        channel=Channel(raw["channel"]),
        customer_name=raw["customer_name"],
        customer_email=raw.get("customer_email"),
        customer_phone=raw.get("customer_phone"),
        subject=raw.get("subject"),
        message=raw["message"],
        received_at=raw.get("timestamp", raw.get("received_at", "")),
        metadata={},
        category=raw.get("category"),
    )


# --- Fixtures ---

@pytest.fixture(scope="module")
def tkt_002():
    return _load_ticket("TKT-002")

@pytest.fixture(scope="module")
def tkt_006():
    return _load_ticket("TKT-006")

@pytest.fixture(scope="module")
def tkt_025():
    return _load_ticket("TKT-025")

@pytest.fixture(scope="module")
def tkt_032():
    return _load_ticket("TKT-032")

@pytest.fixture(scope="module")
def tkt_044():
    return _load_ticket("TKT-044")


# --- Tests ---

def test_tkt002_produces_agent_response(tkt_002):
    """TKT-002 (email, neutral) → AgentResponse without exception."""
    from src.agent.prototype import process_ticket
    from src.agent.models import AgentResponse

    result = process_ticket(tkt_002)
    assert isinstance(result, AgentResponse)
    assert result.formatted_response
    assert result.escalation is not None


def test_tkt006_escalates(tkt_006):
    """TKT-006 (furious + human request) → should_escalate=True."""
    from src.agent.prototype import process_ticket

    result = process_ticket(tkt_006)
    assert result.escalation.should_escalate is True, (
        f"Expected escalation; reason: {result.escalation.reason!r}"
    )


def test_tkt025_whatsapp_not_escalated(tkt_025):
    """TKT-025 (WhatsApp) → should_escalate=False, len ≤ 1600."""
    from src.agent.prototype import process_ticket

    result = process_ticket(tkt_025)
    assert result.escalation.should_escalate is False
    assert len(result.formatted_response) <= 1600, (
        f"WhatsApp response too long: {len(result.formatted_response)}"
    )


def test_tkt032_whatsapp_not_escalated(tkt_032):
    """TKT-032 (WhatsApp gibberish) → should_escalate=False, AgentResponse returned."""
    from src.agent.prototype import process_ticket
    from src.agent.models import AgentResponse

    result = process_ticket(tkt_032)
    assert isinstance(result, AgentResponse)
    assert result.escalation.should_escalate is False
    assert result.formatted_response


def test_tkt044_gdpr_escalates(tkt_044):
    """TKT-044 (web_form GDPR) → should_escalate=True."""
    from src.agent.prototype import process_ticket

    result = process_ticket(tkt_044)
    assert result.escalation.should_escalate is True, (
        f"Expected GDPR to escalate; reason: {result.escalation.reason!r}"
    )


def test_all_five_tickets_run_under_60s():
    """All 5 test tickets process in < 60s total."""
    from src.agent.prototype import process_ticket

    ids = ["TKT-002", "TKT-006", "TKT-025", "TKT-032", "TKT-044"]
    start = time.monotonic()
    for tid in ids:
        msg = _load_ticket(tid)
        result = process_ticket(msg)
        assert result.formatted_response

    elapsed = time.monotonic() - start
    assert elapsed < 60, f"Total run time {elapsed:.1f}s exceeded 60s"


def test_tkt002_email_response_format(tkt_002):
    """TKT-002 email response starts with 'Dear James,' and contains NexaFlow signature."""
    from src.agent.prototype import process_ticket

    result = process_ticket(tkt_002)
    if not result.escalation.should_escalate:
        assert result.formatted_response.startswith("Dear James,"), (
            f"Email should start with 'Dear James,'; got: {result.formatted_response[:40]!r}"
        )
        assert "NexaFlow" in result.formatted_response


def test_processing_time_positive(tkt_025):
    """processing_time_ms > 0 and prompt_datetime contains PKT."""
    from src.agent.prototype import process_ticket

    result = process_ticket(tkt_025)
    assert result.processing_time_ms > 0
    assert "PKT" in result.prompt_datetime
