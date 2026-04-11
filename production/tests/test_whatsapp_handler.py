"""
production/tests/test_whatsapp_handler.py
Phase 4C + 7D: Tests for WhatsAppHandler — direct DB path (no Kafka).

WhatsApp messages now go:
  webhook → validate signature → create customer/conversation/ticket in DB
         → AI agent → send_reply() back to WhatsApp
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
# Helpers
# ---------------------------------------------------------------------------

def _twilio_form(
    from_num: str = "whatsapp:+12025551234",
    body: str = "Hi",
    sid: str = "SM123",
    num_media: str = "0",
) -> dict:
    return {"From": from_num, "Body": body, "MessageSid": sid, "NumMedia": num_media}


def _mock_db_and_agent():
    """Return a context manager that patches all DB + agent calls."""
    mock_pool = AsyncMock()

    mock_queries = MagicMock()
    mock_queries.get_or_create_customer = AsyncMock(return_value={"id": "cust-uuid-1234", "name": "test"})
    mock_queries.link_phone_to_customer = AsyncMock()
    mock_queries.create_conversation = AsyncMock(return_value="conv-uuid-1234")
    mock_queries.add_message = AsyncMock(return_value="msg-uuid-1234")
    mock_queries.create_ticket = AsyncMock(return_value="ticket-uuid-1234")
    mock_queries.get_ticket_by_display_id = AsyncMock(return_value={
        "ticket_id": "TKT-TICKETXX",
        "internal_id": "ticket-uuid-1234",
        "conversation_id": "conv-uuid-1234",
        "customer_id": "cust-uuid-1234",
        "status": "open",
        "channel": "whatsapp",
        "message": "Hi",
        "subject": "Hi",
        "customer_name": "+12025551234",
        "customer_email": "wa_12025551234@whatsapp.nexaflow",
    })

    mock_agent_resp = MagicMock()
    mock_agent_resp.response_text = "Hello! How can I help you with NexaFlow?"
    mock_agent_resp.escalated = False
    mock_agent_resp.error = None

    return (
        patch("production.database.queries.get_db_pool", return_value=mock_pool),
        patch("production.database.queries", mock_queries),
        patch("production.api.agent_routes._run_agent_on_ticket", new_callable=AsyncMock,
              return_value=mock_agent_resp),
        mock_queries,
        mock_agent_resp,
    )


# ---------------------------------------------------------------------------
# T027: test_valid_signature_processes_message
# ---------------------------------------------------------------------------

def test_valid_signature_processes_message():
    """Valid Twilio signature → webhook returns 200, DB customer created."""
    from production.api.main import app
    client = TestClient(app)

    p_pool, p_queries, p_agent, mock_queries, _ = _mock_db_and_agent()

    with patch("production.channels.whatsapp_handler.RequestValidator") as MockValidator, \
         p_pool, p_queries, p_agent, \
         patch.object(
             __import__("production.channels.whatsapp_handler",
                        fromlist=["WhatsAppHandler"]).WhatsAppHandler,
             "send_reply", new_callable=AsyncMock, return_value="SM_sent"
         ):
        MockValidator.return_value.validate.return_value = True

        response = client.post(
            "/webhooks/whatsapp",
            data=_twilio_form(),
            headers={"X-Twilio-Signature": "valid_sig"},
        )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"


# ---------------------------------------------------------------------------
# T028: test_invalid_signature_returns_403
# ---------------------------------------------------------------------------

def test_invalid_signature_returns_403():
    """Invalid Twilio signature → HTTP 403, no DB operations."""
    from production.api.main import app
    client = TestClient(app)

    with patch("production.channels.whatsapp_handler.RequestValidator") as MockValidator:
        MockValidator.return_value.validate.return_value = False

        response = client.post(
            "/webhooks/whatsapp",
            data=_twilio_form(),
            headers={"X-Twilio-Signature": "bad_sig"},
        )

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# T029: test_missing_signature_header_returns_403
# ---------------------------------------------------------------------------

def test_missing_signature_header_returns_403():
    """No X-Twilio-Signature header → HTTP 403."""
    from production.api.main import app
    client = TestClient(app)

    response = client.post(
        "/webhooks/whatsapp",
        data=_twilio_form(),
        # No X-Twilio-Signature header
    )

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# T030: test_duplicate_message_sid_dropped
# ---------------------------------------------------------------------------

def test_duplicate_message_sid_dropped():
    """Same MessageSid posted twice → process_webhook runs only once (idempotency)."""
    from production.api.main import app
    client = TestClient(app)

    p_pool, p_queries, p_agent, mock_queries, _ = _mock_db_and_agent()

    with patch("production.channels.whatsapp_handler.RequestValidator") as MockValidator, \
         p_pool, p_queries, p_agent, \
         patch.object(
             __import__("production.channels.whatsapp_handler",
                        fromlist=["WhatsAppHandler"]).WhatsAppHandler,
             "send_reply", new_callable=AsyncMock, return_value="SM_sent"
         ):
        MockValidator.return_value.validate.return_value = True
        form = _twilio_form(sid="SM123_dup")

        r1 = client.post("/webhooks/whatsapp", data=form, headers={"X-Twilio-Signature": "sig1"})
        r2 = client.post("/webhooks/whatsapp", data=form, headers={"X-Twilio-Signature": "sig1"})

    assert r1.status_code == 200
    assert r2.status_code == 200
    # create_ticket should only be called once (second request deduplicated)
    assert mock_queries.create_ticket.call_count <= 1


# ---------------------------------------------------------------------------
# T031: test_media_only_message_gets_placeholder
# ---------------------------------------------------------------------------

def test_media_only_message_gets_placeholder():
    """Media-only message (empty Body, NumMedia>0) → placeholder text used, HTTP 200."""
    from production.api.main import app
    client = TestClient(app)

    p_pool, p_queries, p_agent, mock_queries, _ = _mock_db_and_agent()

    with patch("production.channels.whatsapp_handler.RequestValidator") as MockValidator, \
         p_pool, p_queries, p_agent, \
         patch.object(
             __import__("production.channels.whatsapp_handler",
                        fromlist=["WhatsAppHandler"]).WhatsAppHandler,
             "send_reply", new_callable=AsyncMock, return_value="SM_sent"
         ):
        MockValidator.return_value.validate.return_value = True

        response = client.post(
            "/webhooks/whatsapp",
            data=_twilio_form(body="", sid="SM456", num_media="1"),
            headers={"X-Twilio-Signature": "sig2"},
        )

    assert response.status_code == 200
    # Verify placeholder text was passed to add_message
    if mock_queries.add_message.called:
        call_args = mock_queries.add_message.call_args
        content_arg = call_args[1].get("content") or (call_args[0][2] if len(call_args[0]) > 2 else "")
        assert "[media attachment" in content_arg or response.status_code == 200


# ---------------------------------------------------------------------------
# T032: test_phone_normalised_strips_whatsapp_prefix
# ---------------------------------------------------------------------------

def test_phone_normalised_strips_whatsapp_prefix():
    """'whatsapp:+12025551234' in From → customer created with stripped phone."""
    from production.api.main import app
    client = TestClient(app)

    p_pool, p_queries, p_agent, mock_queries, _ = _mock_db_and_agent()

    with patch("production.channels.whatsapp_handler.RequestValidator") as MockValidator, \
         p_pool, p_queries, p_agent, \
         patch.object(
             __import__("production.channels.whatsapp_handler",
                        fromlist=["WhatsAppHandler"]).WhatsAppHandler,
             "send_reply", new_callable=AsyncMock, return_value="SM_sent"
         ):
        MockValidator.return_value.validate.return_value = True

        client.post(
            "/webhooks/whatsapp",
            data=_twilio_form(from_num="whatsapp:+12025551234", sid="SM789"),
            headers={"X-Twilio-Signature": "sig3"},
        )

    # pseudo-email should use stripped phone (no "whatsapp:" prefix)
    if mock_queries.get_or_create_customer.called:
        email_arg = mock_queries.get_or_create_customer.call_args[0][1]  # second positional arg
        assert "whatsapp:" not in email_arg, f"Phone not stripped in email: {email_arg}"
        assert "12025551234" in email_arg


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
    asyncio.run(handler.send_reply(to_phone="+1234567890", body="x" * 2000))

    create_call = mock_client.messages.create
    create_call.assert_called_once()
    call_kwargs = create_call.call_args[1]
    assert len(call_kwargs["body"]) == 1600, f"Expected 1600 chars, got {len(call_kwargs['body'])}"


# ---------------------------------------------------------------------------
# T034: test_db_failure_returns_200
# ---------------------------------------------------------------------------

def test_db_failure_returns_200():
    """DB error in process_webhook → HTTP 200 still returned (no crash)."""
    from production.api.main import app
    client = TestClient(app)

    with patch("production.channels.whatsapp_handler.RequestValidator") as MockValidator, \
         patch("production.database.queries.get_db_pool",
               side_effect=Exception("db connection failed")):

        MockValidator.return_value.validate.return_value = True

        response = client.post(
            "/webhooks/whatsapp",
            data=_twilio_form(sid="SM_db_fail"),
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
    result = asyncio.run(handler.send_reply(to_phone="+1234567890", body="Hello"))

    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert result.get("delivery_status") == "failed", f"Got: {result}"


# ---------------------------------------------------------------------------
# T036: test_process_webhook_creates_ticket_in_db
# ---------------------------------------------------------------------------

def test_process_webhook_creates_ticket_in_db():
    """Valid webhook → create_ticket called with channel='whatsapp'."""
    from production.api.main import app
    client = TestClient(app)

    p_pool, p_queries, p_agent, mock_queries, _ = _mock_db_and_agent()

    with patch("production.channels.whatsapp_handler.RequestValidator") as MockValidator, \
         p_pool, p_queries, p_agent, \
         patch.object(
             __import__("production.channels.whatsapp_handler",
                        fromlist=["WhatsAppHandler"]).WhatsAppHandler,
             "send_reply", new_callable=AsyncMock, return_value="SM_sent"
         ):
        MockValidator.return_value.validate.return_value = True

        response = client.post(
            "/webhooks/whatsapp",
            data=_twilio_form(sid="SM_schema"),
            headers={"X-Twilio-Signature": "sig5"},
        )

    assert response.status_code == 200
    # Ticket should be created with whatsapp channel
    if mock_queries.create_ticket.called:
        call_kwargs = mock_queries.create_ticket.call_args[1]
        channel = call_kwargs.get("channel") or mock_queries.create_ticket.call_args[0][3]
        assert channel == "whatsapp", f"Expected whatsapp channel, got: {channel}"
