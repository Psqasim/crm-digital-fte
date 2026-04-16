"""
production/tests/test_gmail_handler.py
Phase 4C + 7E: Tests for GmailHandler — direct-DB flow (no Kafka).
"""

from __future__ import annotations

import base64
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pubsub_payload(history_id: str = "100", message_id: str = "msg_001") -> dict:
    data = json.dumps({"emailAddress": "user@example.com", "historyId": history_id})
    encoded = base64.urlsafe_b64encode(data.encode()).decode().rstrip("=")
    return {
        "message": {"data": encoded, "messageId": message_id, "publishTime": "2026-04-04T00:00:00Z"},
        "subscription": "projects/test-project/subscriptions/gmail-sub",
    }


def _mock_gmail_service(
    history_entries: list | None = None,
    msg_headers: list | None = None,
    msg_body_data: str = "SGVsbG8gd29ybGQ=",
    snippet: str = "Hello world",
    thread_id: str = "thread_abc",
) -> MagicMock:
    if history_entries is None:
        history_entries = [{"messagesAdded": [{"message": {"id": "msg_001"}}]}]
    if msg_headers is None:
        msg_headers = [
            {"name": "From", "value": "Alice <alice@example.com>"},
            {"name": "Subject", "value": "Help needed"},
        ]
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
    service.users.return_value.history.return_value.list.return_value.execute.return_value = {
        "history": history_entries,
        "historyId": "101",
    }
    service.users.return_value.messages.return_value.get.return_value.execute.return_value = msg_payload
    service.users.return_value.messages.return_value.send.return_value.execute.return_value = {
        "id": "sent_001", "threadId": thread_id,
    }
    return service


FAKE_TICKET = {
    "ticket_id": "TKT-ABCD1234",
    "internal_id": "abcd1234-0000-0000-0000-000000000000",
    "conversation_id": "conv-uuid-001",
    "customer_id": "cust-uuid-001",
    "customer_name": "Alice",
    "customer_email": "alice@example.com",
    "channel": "email",
    "subject": "Help needed",
    "message": "Hello world",
    "status": "open",
    "category": None,
    "priority": "medium",
    "ai_response": None,
    "messages": [],
    "created_at": None,
    "updated_at": None,
    "resolved_at": None,
}

FAKE_AGENT_RESP = MagicMock(
    ticket_id="TKT-ABCD1234",
    response_text="Hi Alice, we are looking into your issue.",
    escalated=False,
    error=None,
)


def _db_patches(claim_return=True):
    """Return a list of patch context managers for all DB functions."""
    return [
        patch("production.database.queries.get_db_pool", new_callable=AsyncMock, return_value=MagicMock()),
        patch("production.database.queries.claim_gmail_message", new_callable=AsyncMock, return_value=claim_return),
        patch("production.database.queries.get_or_create_customer", new_callable=AsyncMock, return_value={"id": "cust-uuid-001"}),
        patch("production.database.queries.create_conversation", new_callable=AsyncMock, return_value="conv-uuid-001"),
        patch("production.database.queries.add_message", new_callable=AsyncMock, return_value="msg-uuid-001"),
        patch("production.database.queries.create_ticket", new_callable=AsyncMock, return_value="TKT-ABCD1234"),
        patch("production.database.queries.get_ticket_by_display_id", new_callable=AsyncMock, return_value=FAKE_TICKET),
        patch("production.database.queries.update_ticket_status", new_callable=AsyncMock),
        patch("production.api.agent_routes._run_agent_on_ticket", new_callable=AsyncMock, return_value=FAKE_AGENT_RESP),
    ]


# ---------------------------------------------------------------------------
# Fixture: reset module-level state
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_gmail_handler_state():
    import production.channels.gmail_handler as gh
    gh._last_history_id = None
    gh._handler_instance = None
    yield
    gh._last_history_id = None
    gh._handler_instance = None


# ---------------------------------------------------------------------------
# T007: valid push → DB records created
# ---------------------------------------------------------------------------

def test_process_pub_sub_push_valid():
    """Valid Pub/Sub push → claim, customer, ticket all created."""
    import asyncio
    import production.channels.gmail_handler as gh
    import production.database.queries as q

    handler = gh.GmailHandler()
    handler.service = _mock_gmail_service()
    gh._last_history_id = "99"

    patches = _db_patches(claim_return=True)
    with patches[0], patches[1] as mock_claim, patches[2] as mock_customer, \
         patches[3], patches[4], patches[5] as mock_ticket, patches[6], patches[7], patches[8]:
        asyncio.run(handler.process_pub_sub_push(_make_pubsub_payload(history_id="100")))

    mock_claim.assert_called_once()
    mock_customer.assert_called_once()
    mock_ticket.assert_called_once()


# ---------------------------------------------------------------------------
# T008: DB dedup — already claimed → skip
# ---------------------------------------------------------------------------

def test_process_pub_sub_push_dedup():
    """claim_gmail_message returns False → no customer/ticket created."""
    import asyncio
    import production.channels.gmail_handler as gh

    handler = gh.GmailHandler()
    handler.service = _mock_gmail_service()
    gh._last_history_id = "99"

    patches = _db_patches(claim_return=False)
    with patches[0], patches[1], patches[2] as mock_customer, \
         patches[3], patches[4], patches[5] as mock_ticket, patches[6], patches[7], patches[8]:
        asyncio.run(handler.process_pub_sub_push(_make_pubsub_payload(history_id="100")))

    mock_customer.assert_not_called()
    mock_ticket.assert_not_called()


# ---------------------------------------------------------------------------
# T009: no messagesAdded → nothing processed
# ---------------------------------------------------------------------------

def test_process_pub_sub_push_no_new_messages():
    """history.list returns no messagesAdded → no DB writes."""
    import asyncio
    import production.channels.gmail_handler as gh

    handler = gh.GmailHandler()
    handler.service = _mock_gmail_service(history_entries=[{"labelsAdded": []}])
    gh._last_history_id = "99"

    patches = _db_patches()
    with patches[0], patches[1], patches[2], \
         patches[3], patches[4], patches[5] as mock_ticket, patches[6], patches[7], patches[8]:
        asyncio.run(handler.process_pub_sub_push(_make_pubsub_payload(history_id="100")))

    mock_ticket.assert_not_called()


# ---------------------------------------------------------------------------
# T010: send_reply preserves thread_id
# ---------------------------------------------------------------------------

def test_send_reply_preserves_thread_id():
    """send_reply() passes correct threadId to Gmail API."""
    import asyncio
    from production.channels.gmail_handler import GmailHandler

    handler = GmailHandler()
    handler.service = _mock_gmail_service(thread_id="thread123")

    asyncio.run(handler.send_reply(thread_id="thread123", to_email="x@y.com", body="Hello"))

    send_call = handler.service.users.return_value.messages.return_value.send
    body_arg = send_call.call_args[1].get("body") or send_call.call_args[0][0] if send_call.call_args[0] else {}
    if not body_arg:
        body_arg = send_call.call_args_list[0][1].get("body", {})
    assert body_arg.get("threadId") == "thread123"


# ---------------------------------------------------------------------------
# T011: missing credentials → no crash
# ---------------------------------------------------------------------------

def test_missing_credentials_does_not_crash(capsys):
    """setup_credentials() without env vars logs error, service stays None."""
    import asyncio
    import os
    from production.channels.gmail_handler import GmailHandler

    handler = GmailHandler()
    env_clean = {k: v for k, v in os.environ.items() if "GMAIL" not in k and "GOOGLE" not in k}
    with patch.dict("os.environ", env_clean, clear=True):
        asyncio.run(handler.setup_credentials())

    assert handler.service is None


# ---------------------------------------------------------------------------
# T012: malformed base64 → HTTP 200
# ---------------------------------------------------------------------------

def test_base64_decode_error_returns_200():
    """Malformed base64 in Pub/Sub payload → HTTP 200, no 5xx."""
    from production.api.main import app

    client = TestClient(app)
    response = client.post("/webhooks/gmail", json={
        "message": {"data": "!!!invalid!!!", "messageId": "1"},
        "subscription": "s",
    })
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# T013: HTML-only email → creates ticket (falls back to snippet)
# ---------------------------------------------------------------------------

def test_html_only_email_extracts_snippet():
    """HTML-only email → ticket still created using snippet as body."""
    import asyncio
    import production.channels.gmail_handler as gh

    html_service = MagicMock()
    html_service.users.return_value.history.return_value.list.return_value.execute.return_value = {
        "history": [{"messagesAdded": [{"message": {"id": "msg_html"}}]}],
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
    html_service.users.return_value.messages.return_value.send.return_value.execute.return_value = {"id": "s1"}

    handler = gh.GmailHandler()
    handler.service = html_service
    gh._last_history_id = "99"

    patches = _db_patches(claim_return=True)
    with patches[0], patches[1], patches[2], \
         patches[3], patches[4], patches[5] as mock_ticket, patches[6], patches[7], patches[8]:
        asyncio.run(handler.process_pub_sub_push(_make_pubsub_payload(history_id="100")))

    mock_ticket.assert_called_once()


# ---------------------------------------------------------------------------
# T014: history.list API error → HTTP 200
# ---------------------------------------------------------------------------

def test_history_list_api_error_does_not_crash():
    """history.list raises HttpError → /webhooks/gmail returns HTTP 200."""
    from googleapiclient.errors import HttpError
    from production.api.main import app
    import production.channels.gmail_handler as gh

    client = TestClient(app)
    gh._last_history_id = "99"

    service = MagicMock()
    service.users.return_value.history.return_value.list.return_value.execute.side_effect = (
        HttpError(resp=MagicMock(status=500), content=b"error")
    )
    test_handler = gh.GmailHandler()
    test_handler.service = service

    with patch.object(gh, "_handler_instance", test_handler), \
         patch("production.database.queries.get_db_pool", new_callable=AsyncMock, return_value=MagicMock()):
        response = client.post("/webhooks/gmail", json=_make_pubsub_payload(history_id="999"))

    assert response.status_code == 200


# ---------------------------------------------------------------------------
# T015: DB error during processing → HTTP 200
# ---------------------------------------------------------------------------

def test_db_failure_does_not_crash():
    """DB error during processing → /webhooks/gmail still returns HTTP 200."""
    from production.api.main import app
    import production.channels.gmail_handler as gh

    client = TestClient(app)
    gh._last_history_id = "99"

    test_handler = gh.GmailHandler()
    test_handler.service = _mock_gmail_service()

    with patch.object(gh, "_handler_instance", test_handler), \
         patch("production.database.queries.get_db_pool", new_callable=AsyncMock, return_value=MagicMock()), \
         patch("production.database.queries.claim_gmail_message", new_callable=AsyncMock, side_effect=Exception("DB down")):
        response = client.post("/webhooks/gmail", json=_make_pubsub_payload(history_id="200"))

    assert response.status_code == 200


# ---------------------------------------------------------------------------
# T016: own email skipped → no reply loop
# ---------------------------------------------------------------------------

def test_own_email_skipped():
    """Email from GMAIL_USER_EMAIL → skipped to avoid infinite reply loop."""
    import asyncio
    import production.channels.gmail_handler as gh

    service = _mock_gmail_service(msg_headers=[
        {"name": "From", "value": "mmfake78@gmail.com"},
        {"name": "Subject", "value": "Test"},
    ])
    handler = gh.GmailHandler()
    handler.service = service
    gh._last_history_id = "99"

    patches = _db_patches(claim_return=True)
    with patches[0], patches[1], patches[2], \
         patches[3], patches[4], patches[5] as mock_ticket, patches[6], patches[7], patches[8], \
         patch.dict("os.environ", {"GMAIL_USER_EMAIL": "mmfake78@gmail.com"}):
        asyncio.run(handler.process_pub_sub_push(_make_pubsub_payload(history_id="100")))

    mock_ticket.assert_not_called()
