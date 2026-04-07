"""
production/tests/test_whatsapp_handler.py
Phase 4C: Tests for WhatsAppHandler — 10 tests (T027–T036).

Tests use FastAPI TestClient for endpoint tests and unittest.mock for
Twilio API / Kafka mocks.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixture: reset module-level state between tests
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_whatsapp_handler_state():
    """Reset module-level _seen_message_sids before each test."""
    try:
        import production.channels.whatsapp_handler as wh
        wh._seen_message_sids.clear()
        # Reset the singleton handler so each test starts fresh
        wh._handler_instance = None
    except (ImportError, AttributeError):
        pass
    yield
    try:
        import production.channels.whatsapp_handler as wh
        wh._seen_message_sids.clear()
        wh._handler_instance = None
    except (ImportError, AttributeError):
        pass


# ---------------------------------------------------------------------------
# Helper: standard Twilio form payload
# ---------------------------------------------------------------------------

def _twilio_form(
    from_num: str = "whatsapp:+12025551234",
    body: str = "Hi",
    sid: str = "SM123",
    num_media: str = "0",
) -> dict:
    return {"From": from_num, "Body": body, "MessageSid": sid, "NumMedia": num_media}


# ---------------------------------------------------------------------------
# T027: test_valid_signature_processes_message
# ---------------------------------------------------------------------------

def test_valid_signature_processes_message():
    """Valid Twilio signature → publish_ticket called once with channel='whatsapp'."""
    from src.agent.models import TicketMessage
    from production.api.main import app

    client = TestClient(app)

    with patch("production.channels.whatsapp_handler.RequestValidator") as MockValidator, \
         patch("production.channels.whatsapp_handler.publish_ticket", new_callable=AsyncMock) as mock_publish:

        MockValidator.return_value.validate.return_value = True

        response = client.post(
            "/webhooks/whatsapp",
            data=_twilio_form(),
            headers={"X-Twilio-Signature": "valid_sig"},
        )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    mock_publish.assert_called_once()
    ticket = mock_publish.call_args[0][0]
    assert isinstance(ticket, TicketMessage)
    assert str(ticket.channel) in ("whatsapp", "Channel.WHATSAPP")


# ---------------------------------------------------------------------------
# T028: test_invalid_signature_returns_403
# ---------------------------------------------------------------------------

def test_invalid_signature_returns_403():
    """Invalid Twilio signature → HTTP 403, publish_ticket never called."""
    from production.api.main import app

    client = TestClient(app)

    with patch("production.channels.whatsapp_handler.RequestValidator") as MockValidator, \
         patch("production.channels.whatsapp_handler.publish_ticket", new_callable=AsyncMock) as mock_publish:

        MockValidator.return_value.validate.return_value = False

        response = client.post(
            "/webhooks/whatsapp",
            data=_twilio_form(),
            headers={"X-Twilio-Signature": "bad_sig"},
        )

    assert response.status_code == 403
    assert mock_publish.call_count == 0


# ---------------------------------------------------------------------------
# T029: test_missing_signature_header_returns_403
# ---------------------------------------------------------------------------

def test_missing_signature_header_returns_403():
    """No X-Twilio-Signature header → HTTP 403, publish_ticket never called."""
    from production.api.main import app

    client = TestClient(app)

    with patch("production.channels.whatsapp_handler.publish_ticket", new_callable=AsyncMock) as mock_publish:
        response = client.post(
            "/webhooks/whatsapp",
            data=_twilio_form(),
            # No X-Twilio-Signature header
        )

    assert response.status_code == 403
    assert mock_publish.call_count == 0


# ---------------------------------------------------------------------------
# T030: test_duplicate_message_sid_dropped
# ---------------------------------------------------------------------------

def test_duplicate_message_sid_dropped():
    """Same MessageSid posted twice → publish_ticket called exactly once."""
    from production.api.main import app

    client = TestClient(app)

    with patch("production.channels.whatsapp_handler.RequestValidator") as MockValidator, \
         patch("production.channels.whatsapp_handler.publish_ticket", new_callable=AsyncMock) as mock_publish:

        MockValidator.return_value.validate.return_value = True
        form = _twilio_form(sid="SM123")

        client.post("/webhooks/whatsapp", data=form, headers={"X-Twilio-Signature": "sig1"})
        client.post("/webhooks/whatsapp", data=form, headers={"X-Twilio-Signature": "sig1"})

    assert mock_publish.call_count == 1, f"Expected 1 call, got {mock_publish.call_count}"


# ---------------------------------------------------------------------------
# T031: test_media_only_message_gets_placeholder
# ---------------------------------------------------------------------------

def test_media_only_message_gets_placeholder():
    """Media-only message (empty Body, NumMedia>0) → placeholder text, HTTP 200."""
    from production.api.main import app

    client = TestClient(app)

    captured = []
    async def capture(ticket):
        captured.append(ticket)

    with patch("production.channels.whatsapp_handler.RequestValidator") as MockValidator, \
         patch("production.channels.whatsapp_handler.publish_ticket", side_effect=capture):

        MockValidator.return_value.validate.return_value = True

        response = client.post(
            "/webhooks/whatsapp",
            data=_twilio_form(body="", sid="SM456", num_media="1"),
            headers={"X-Twilio-Signature": "sig2"},
        )

    assert response.status_code == 200
    assert len(captured) == 1
    assert captured[0].message == "[media attachment — no text]", f"Got: {captured[0].message}"


# ---------------------------------------------------------------------------
# T032: test_phone_normalised_strips_whatsapp_prefix
# ---------------------------------------------------------------------------

def test_phone_normalised_strips_whatsapp_prefix():
    """'whatsapp:+12025551234' in From field → customer_phone='+12025551234'."""
    from production.api.main import app

    client = TestClient(app)

    captured = []
    async def capture(ticket):
        captured.append(ticket)

    with patch("production.channels.whatsapp_handler.RequestValidator") as MockValidator, \
         patch("production.channels.whatsapp_handler.publish_ticket", side_effect=capture):

        MockValidator.return_value.validate.return_value = True

        client.post(
            "/webhooks/whatsapp",
            data=_twilio_form(from_num="whatsapp:+12025551234", sid="SM789"),
            headers={"X-Twilio-Signature": "sig3"},
        )

    assert len(captured) == 1
    assert captured[0].customer_phone == "+12025551234", f"Got: {captured[0].customer_phone}"


# ---------------------------------------------------------------------------
# T033: test_send_reply_truncates_at_1600_chars
# ---------------------------------------------------------------------------

def test_send_reply_truncates_at_1600_chars():
    """send_reply with 2000-char body → Twilio create called with body of len 1600."""
    from production.channels.whatsapp_handler import WhatsAppHandler

    handler = WhatsAppHandler()
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(sid="SM_sent")
    handler.twilio_client = mock_client

    import asyncio
    asyncio.run(
        handler.send_reply(to_phone="+1234567890", body="x" * 2000)
    )

    create_call = mock_client.messages.create
    create_call.assert_called_once()
    call_kwargs = create_call.call_args[1]
    assert len(call_kwargs["body"]) == 1600, f"Expected 1600 chars, got {len(call_kwargs['body'])}"


# ---------------------------------------------------------------------------
# T034: test_kafka_publish_failure_returns_200
# ---------------------------------------------------------------------------

def test_kafka_publish_failure_returns_200():
    """publish_ticket raises Exception → HTTP 200, error logged, no crash."""
    from production.api.main import app

    client = TestClient(app)

    with patch("production.channels.whatsapp_handler.RequestValidator") as MockValidator, \
         patch("production.channels.whatsapp_handler.publish_ticket",
               new_callable=AsyncMock, side_effect=Exception("broker down")):

        MockValidator.return_value.validate.return_value = True

        response = client.post(
            "/webhooks/whatsapp",
            data=_twilio_form(sid="SM_kafka_fail"),
            headers={"X-Twilio-Signature": "sig4"},
        )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"


# ---------------------------------------------------------------------------
# T035: test_twilio_client_error_returns_failed_status
# ---------------------------------------------------------------------------

def test_twilio_client_error_returns_failed_status():
    """send_reply raises TwilioException → returns dict with delivery_status='failed'."""
    from twilio.base.exceptions import TwilioException
    from production.channels.whatsapp_handler import WhatsAppHandler

    handler = WhatsAppHandler()
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = TwilioException("auth failed")
    handler.twilio_client = mock_client

    import asyncio
    result = asyncio.run(
        handler.send_reply(to_phone="+1234567890", body="Hello")
    )

    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert result.get("delivery_status") == "failed", f"Got: {result}"


# ---------------------------------------------------------------------------
# T036: test_ticket_message_schema_matches_prototype
# ---------------------------------------------------------------------------

def test_ticket_message_schema_matches_prototype():
    """TicketMessage from process_webhook has all required fields."""
    from src.agent.models import TicketMessage
    from production.api.main import app

    client = TestClient(app)

    captured = []
    async def capture(ticket):
        captured.append(ticket)

    with patch("production.channels.whatsapp_handler.RequestValidator") as MockValidator, \
         patch("production.channels.whatsapp_handler.publish_ticket", side_effect=capture):

        MockValidator.return_value.validate.return_value = True

        client.post(
            "/webhooks/whatsapp",
            data=_twilio_form(sid="SM_schema"),
            headers={"X-Twilio-Signature": "sig5"},
        )

    assert len(captured) == 1
    msg = captured[0]
    assert isinstance(msg, TicketMessage)
    assert str(msg.channel) in ("whatsapp", "Channel.WHATSAPP")
    assert msg.metadata.get("message_sid") is not None, f"message_sid missing from metadata: {msg.metadata}"
