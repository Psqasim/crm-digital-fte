"""
production/tests/test_gmail_handler.py
Phase 4C: Tests for GmailHandler — 10 tests (T007–T016).

Tests use FastAPI TestClient for endpoint tests and unittest.mock for
Gmail API / Kafka mocks.
"""

from __future__ import annotations

import base64
import json
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers — build a minimal valid Pub/Sub payload
# ---------------------------------------------------------------------------

def _make_pubsub_payload(history_id: str = "100", message_id: str = "msg_001") -> dict:
    """Produce a base64url-encoded Pub/Sub push payload from Gmail."""
    data = json.dumps({"emailAddress": "user@example.com", "historyId": history_id})
    encoded = base64.urlsafe_b64encode(data.encode()).decode().rstrip("=")
    return {
        "message": {"data": encoded, "messageId": message_id, "publishTime": "2026-04-04T00:00:00Z"},
        "subscription": "projects/test-project/subscriptions/gmail-sub",
    }


def _mock_gmail_service(
    history_entries: list | None = None,
    msg_headers: list | None = None,
    msg_body_data: str = "SGVsbG8gd29ybGQ=",  # b64 "Hello world"
    snippet: str = "Hello world",
    thread_id: str = "thread_abc",
) -> MagicMock:
    """Build a mock Gmail service object."""
    if history_entries is None:
        history_entries = [{"messages": [{"id": "msg_001"}]}]
    if msg_headers is None:
        msg_headers = [
            {"name": "From", "value": "Alice <alice@example.com>"},
            {"name": "Subject", "value": "Help needed"},
        ]

    # Build the message payload
    msg_payload = {
        "id": "msg_001",
        "threadId": thread_id,
        "snippet": snippet,
        "payload": {
            "headers": msg_headers,
            "mimeType": "text/plain",
            "body": {"data": msg_body_data},
        },
    }

    service = MagicMock()
    # history().list().execute()
    service.users.return_value.history.return_value.list.return_value.execute.return_value = {
        "history": history_entries,
        "historyId": "101",
    }
    # messages().get().execute()
    service.users.return_value.messages.return_value.get.return_value.execute.return_value = msg_payload
    # messages().send().execute()
    service.users.return_value.messages.return_value.send.return_value.execute.return_value = {
        "id": "sent_001",
        "threadId": thread_id,
    }
    return service


# ---------------------------------------------------------------------------
# Fixture: reset module-level state between tests
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_gmail_handler_state():
    """Reset module-level _seen_message_ids, _last_history_id before each test."""
    try:
        import production.channels.gmail_handler as gh
        gh._seen_message_ids.clear()
        gh._last_history_id = None
    except (ImportError, AttributeError):
        pass  # Module not yet implemented — that's expected for early tests
    yield
    try:
        import production.channels.gmail_handler as gh
        gh._seen_message_ids.clear()
        gh._last_history_id = None
    except (ImportError, AttributeError):
        pass


# ---------------------------------------------------------------------------
# T007: test_process_pub_sub_push_valid
# ---------------------------------------------------------------------------

def test_process_pub_sub_push_valid():
    """Valid Pub/Sub push → publish_ticket called once with channel='email'."""
    from production.channels.gmail_handler import GmailHandler
    from src.agent.models import TicketMessage

    handler = GmailHandler()
    handler.service = _mock_gmail_service()

    import production.channels.gmail_handler as gh
    gh._last_history_id = "99"  # Set prior historyId so new one (100) is different

    with patch("production.channels.gmail_handler.publish_ticket", new_callable=AsyncMock) as mock_publish:
        import asyncio
        asyncio.run(
            handler.process_pub_sub_push(_make_pubsub_payload(history_id="100"))
        )

    mock_publish.assert_called_once()
    ticket = mock_publish.call_args[0][0]
    assert isinstance(ticket, TicketMessage)
    assert ticket.channel == "email" or str(ticket.channel) in ("email", "Channel.EMAIL")


# ---------------------------------------------------------------------------
# T008: test_process_pub_sub_push_dedup
# ---------------------------------------------------------------------------

def test_process_pub_sub_push_dedup():
    """Same historyId twice → publish_ticket called exactly once."""
    from production.channels.gmail_handler import GmailHandler

    handler = GmailHandler()
    handler.service = _mock_gmail_service()

    import production.channels.gmail_handler as gh
    gh._last_history_id = "99"

    with patch("production.channels.gmail_handler.publish_ticket", new_callable=AsyncMock) as mock_publish:
        import asyncio
        payload = _make_pubsub_payload(history_id="100")
        asyncio.run(handler.process_pub_sub_push(payload))
        asyncio.run(handler.process_pub_sub_push(payload))

    assert mock_publish.call_count == 1, f"Expected 1 call, got {mock_publish.call_count}"


# ---------------------------------------------------------------------------
# T009: test_process_pub_sub_push_no_new_messages
# ---------------------------------------------------------------------------

def test_process_pub_sub_push_no_new_messages():
    """history.list returns no messagesAdded → publish_ticket never called."""
    from production.channels.gmail_handler import GmailHandler

    handler = GmailHandler()
    # Override: history response with no messagesAdded entries
    service = _mock_gmail_service(history_entries=[{"labelsAdded": []}])
    handler.service = service

    import production.channels.gmail_handler as gh
    gh._last_history_id = "99"

    with patch("production.channels.gmail_handler.publish_ticket", new_callable=AsyncMock) as mock_publish:
        import asyncio
        asyncio.run(
            handler.process_pub_sub_push(_make_pubsub_payload(history_id="100"))
        )

    assert mock_publish.call_count == 0


# ---------------------------------------------------------------------------
# T010: test_send_reply_preserves_thread_id
# ---------------------------------------------------------------------------

def test_send_reply_preserves_thread_id():
    """send_reply() includes correct threadId in Gmail send payload."""
    from production.channels.gmail_handler import GmailHandler

    handler = GmailHandler()
    handler.service = _mock_gmail_service(thread_id="thread123")

    import asyncio
    asyncio.run(
        handler.send_reply(thread_id="thread123", to_email="x@y.com", body="Hello")
    )

    send_call = handler.service.users.return_value.messages.return_value.send
    call_kwargs = send_call.call_args
    # The body dict passed to send() must contain threadId
    body_arg = call_kwargs[1].get("body") or call_kwargs[0][0] if call_kwargs[0] else None
    if body_arg is None:
        # Try kwargs-only form: send(userId='me', body={...})
        all_kwargs = send_call.call_args_list[0]
        body_arg = all_kwargs[1].get("body", {})
    assert body_arg.get("threadId") == "thread123", f"threadId not in send body: {body_arg}"


# ---------------------------------------------------------------------------
# T011: test_missing_credentials_does_not_crash
# ---------------------------------------------------------------------------

def test_missing_credentials_does_not_crash(capsys):
    """setup_credentials() without GMAIL_CREDENTIALS_JSON logs error, no exception."""
    from production.channels.gmail_handler import GmailHandler

    handler = GmailHandler()
    with patch.dict("os.environ", {}, clear=True):
        # Remove Gmail-related env vars
        import os
        env_without_gmail = {k: v for k, v in os.environ.items() if "GMAIL" not in k}
        with patch.dict("os.environ", env_without_gmail, clear=True):
            import asyncio
            asyncio.run(handler.setup_credentials())

    # Should not raise — check stderr has something
    captured = capsys.readouterr()
    assert len(captured.err) > 0 or handler.service is None  # either logged or just None service


# ---------------------------------------------------------------------------
# T012: test_base64_decode_error_returns_200
# ---------------------------------------------------------------------------

def test_base64_decode_error_returns_200():
    """Malformed base64 data in Pub/Sub payload → HTTP 200, no 5xx."""
    from production.api.main import app

    client = TestClient(app)
    bad_payload = {
        "message": {"data": "!!!invalid_base64!!!", "messageId": "1"},
        "subscription": "s",
    }
    response = client.post("/webhooks/gmail", json=bad_payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"


# ---------------------------------------------------------------------------
# T013: test_html_only_email_extracts_snippet
# ---------------------------------------------------------------------------

def test_html_only_email_extracts_snippet():
    """HTML-only email → TicketMessage.message falls back to 'snippet' field."""
    from production.channels.gmail_handler import GmailHandler

    html_service = MagicMock()
    html_service.users.return_value.history.return_value.list.return_value.execute.return_value = {
        "history": [{"messages": [{"id": "msg_html"}]}],
        "historyId": "101",
    }
    html_service.users.return_value.messages.return_value.get.return_value.execute.return_value = {
        "id": "msg_html",
        "threadId": "t_html",
        "snippet": "Preview text",
        "payload": {
            "headers": [
                {"name": "From", "value": "Bob <bob@example.com>"},
                {"name": "Subject", "value": "HTML only"},
            ],
            "mimeType": "text/html",
            "body": {"data": base64.urlsafe_b64encode(b"<b>Preview text</b>").decode()},
        },
    }

    handler = GmailHandler()
    handler.service = html_service

    import production.channels.gmail_handler as gh
    gh._last_history_id = "99"

    captured_ticket = []
    async def capture(ticket):
        captured_ticket.append(ticket)

    with patch("production.channels.gmail_handler.publish_ticket", side_effect=capture):
        import asyncio
        asyncio.run(
            handler.process_pub_sub_push(_make_pubsub_payload(history_id="100", message_id="msg_html_push"))
        )

    assert len(captured_ticket) == 1, "Expected publish_ticket to be called once"
    assert captured_ticket[0].message == "Preview text", f"Got: {captured_ticket[0].message}"


# ---------------------------------------------------------------------------
# T014: test_history_list_api_error_does_not_crash
# ---------------------------------------------------------------------------

def test_history_list_api_error_does_not_crash():
    """history.list raises HttpError → POST to /webhooks/gmail returns HTTP 200."""
    from googleapiclient.errors import HttpError
    from production.api.main import app

    client = TestClient(app)

    import production.channels.gmail_handler as gh
    gh._last_history_id = "99"

    mock_http_error = HttpError(resp=MagicMock(status=500), content=b"error")

    service = MagicMock()
    service.users.return_value.history.return_value.list.return_value.execute.side_effect = mock_http_error

    with patch("production.channels.gmail_handler.GmailHandler.setup_credentials") as mock_setup:
        async def set_service(self_inner=None):
            gh._handler_instance.service = service
        # Directly patch the module-level handler
        pass

    # Patch at module level: replace service on the existing handler
    with patch.object(gh, "_handler_instance", create=True):
        pass

    # Simplest approach: patch process_pub_sub_push to simulate the error path
    original_handler = getattr(gh, "_handler_instance", None)
    test_handler = gh.GmailHandler()
    test_handler.service = service

    with patch.object(gh, "_handler_instance", test_handler):
        response = client.post("/webhooks/gmail", json=_make_pubsub_payload(history_id="999"))

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"


# ---------------------------------------------------------------------------
# T015: test_kafka_publish_failure_does_not_crash
# ---------------------------------------------------------------------------

def test_kafka_publish_failure_does_not_crash():
    """publish_ticket raises Exception → POST to /webhooks/gmail returns HTTP 200."""
    from production.api.main import app

    client = TestClient(app)

    import production.channels.gmail_handler as gh
    gh._last_history_id = "99"

    service = _mock_gmail_service()
    test_handler = gh.GmailHandler()
    test_handler.service = service

    with patch.object(gh, "_handler_instance", test_handler), \
         patch("production.channels.gmail_handler.publish_ticket",
               new_callable=AsyncMock, side_effect=Exception("broker unavailable")):
        response = client.post("/webhooks/gmail", json=_make_pubsub_payload(history_id="200"))

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"


# ---------------------------------------------------------------------------
# T016: test_ticket_message_schema_matches_prototype
# ---------------------------------------------------------------------------

def test_ticket_message_schema_matches_prototype():
    """TicketMessage produced by process_pub_sub_push has all required fields."""
    from production.channels.gmail_handler import GmailHandler
    from src.agent.models import TicketMessage

    handler = GmailHandler()
    handler.service = _mock_gmail_service()

    import production.channels.gmail_handler as gh
    gh._last_history_id = "99"

    captured = []
    async def capture(ticket):
        captured.append(ticket)

    with patch("production.channels.gmail_handler.publish_ticket", side_effect=capture):
        import asyncio
        asyncio.run(
            handler.process_pub_sub_push(_make_pubsub_payload(history_id="100", message_id="msg_schema"))
        )

    assert len(captured) == 1
    msg = captured[0]
    assert isinstance(msg, TicketMessage)
    assert str(msg.channel) in ("email", "Channel.EMAIL")
    assert msg.customer_email is not None
    assert msg.message is not None
    assert msg.received_at is not None
    assert msg.metadata.get("thread_id") is not None
