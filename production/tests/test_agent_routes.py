"""
production/tests/test_agent_routes.py
Phase 4D: Tests for /agent/process/{ticket_id} and /agent/process-pending.

All DB calls and agent invocations are mocked — no live connections required.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from production.api.main import app
from production.agent.customer_success_agent import AgentResponse


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


SAMPLE_TICKET = {
    "ticket_id": "TKT-ABCDEF12",
    "internal_id": "abcdef12-0000-0000-0000-000000000000",
    "conversation_id": "conv-1111-0000-0000-0000-000000000000",
    "customer_id": "cust-2222-0000-0000-0000-000000000000",
    "status": "open",
    "channel": "web",
    "category": "billing",
    "priority": "medium",
    "subject": "Invoice issue",
    "message": "I cannot access my invoice.",
    "customer_name": "Alice",
    "customer_email": "alice@example.com",
    "created_at": None,
    "updated_at": None,
    "resolved_at": None,
}

RESOLVED_RESPONSE = AgentResponse(
    ticket_id="TKT-ABCDEF12",
    response_text="Your invoice is now accessible. Let me know if you need help.",
    channel="web",
    escalated=False,
    escalation_id=None,
    resolution_status="resolved",
    error=None,
)

ESCALATED_RESPONSE = AgentResponse(
    ticket_id="TKT-ABCDEF12",
    response_text="",
    channel="web",
    escalated=True,
    escalation_id="ESC-001",
    resolution_status="pending",
    error=None,
)


# ---------------------------------------------------------------------------
# POST /agent/process/{ticket_id} — success (resolved)
# ---------------------------------------------------------------------------


@patch("production.api.agent_routes.get_db_pool")
@patch("production.api.agent_routes.queries.get_ticket_by_display_id", new_callable=AsyncMock)
@patch("production.api.agent_routes.process_ticket", new_callable=AsyncMock)
@patch("production.api.agent_routes.queries.update_ticket_status", new_callable=AsyncMock)
@patch("production.api.agent_routes.queries.add_message", new_callable=AsyncMock)
def test_process_single_ticket_resolved(
    mock_add_message,
    mock_update_status,
    mock_process,
    mock_get_ticket,
    mock_get_pool,
    client,
):
    mock_pool = AsyncMock()
    mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
    mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_pool.return_value = mock_pool

    mock_get_ticket.return_value = SAMPLE_TICKET
    mock_process.return_value = RESOLVED_RESPONSE

    resp = client.post("/agent/process/TKT-ABCDEF12")

    assert resp.status_code == 200
    data = resp.json()
    assert data["escalated"] is False
    assert data["resolution_status"] == "resolved"
    assert "invoice" in data["response_text"].lower()

    mock_update_status.assert_called_once()
    call_args = mock_update_status.call_args[0]
    assert call_args[2] == "resolved"


# ---------------------------------------------------------------------------
# POST /agent/process/{ticket_id} — escalated
# ---------------------------------------------------------------------------


@patch("production.api.agent_routes.get_db_pool")
@patch("production.api.agent_routes.queries.get_ticket_by_display_id", new_callable=AsyncMock)
@patch("production.api.agent_routes.process_ticket", new_callable=AsyncMock)
@patch("production.api.agent_routes.queries.update_ticket_status", new_callable=AsyncMock)
@patch("production.api.agent_routes.queries.add_message", new_callable=AsyncMock)
def test_process_single_ticket_escalated(
    mock_add_message,
    mock_update_status,
    mock_process,
    mock_get_ticket,
    mock_get_pool,
    client,
):
    mock_pool = AsyncMock()
    mock_get_pool.return_value = mock_pool
    mock_get_ticket.return_value = SAMPLE_TICKET
    mock_process.return_value = ESCALATED_RESPONSE

    resp = client.post("/agent/process/TKT-ABCDEF12")

    assert resp.status_code == 200
    data = resp.json()
    assert data["escalated"] is True
    assert data["escalation_id"] == "ESC-001"

    mock_update_status.assert_called_once()
    call_args = mock_update_status.call_args[0]
    assert call_args[2] == "escalated"


# ---------------------------------------------------------------------------
# POST /agent/process/{ticket_id} — 404 when ticket not found
# ---------------------------------------------------------------------------


@patch("production.api.agent_routes.get_db_pool")
@patch("production.api.agent_routes.queries.get_ticket_by_display_id", new_callable=AsyncMock)
def test_process_single_ticket_not_found(mock_get_ticket, mock_get_pool, client):
    mock_pool = AsyncMock()
    mock_get_pool.return_value = mock_pool
    mock_get_ticket.return_value = None

    resp = client.post("/agent/process/TKT-NOTEXIST")

    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# POST /agent/process-pending — queues tickets
# ---------------------------------------------------------------------------


@patch("production.api.agent_routes.get_db_pool")
@patch("production.api.agent_routes.queries.get_pending_tickets", new_callable=AsyncMock)
def test_process_pending_queues_tickets(mock_get_pending, mock_get_pool, client):
    mock_pool = AsyncMock()
    mock_get_pool.return_value = mock_pool
    mock_get_pending.return_value = [
        {**SAMPLE_TICKET, "ticket_id": "TKT-AAA00001"},
        {**SAMPLE_TICKET, "ticket_id": "TKT-BBB00002"},
    ]

    resp = client.post("/agent/process-pending")

    assert resp.status_code == 200
    data = resp.json()
    assert data["queued"] == 2
    assert "TKT-AAA00001" in data["ticket_ids"]
    assert "TKT-BBB00002" in data["ticket_ids"]


# ---------------------------------------------------------------------------
# POST /agent/process-pending — returns zero when no pending tickets
# ---------------------------------------------------------------------------


@patch("production.api.agent_routes.get_db_pool")
@patch("production.api.agent_routes.queries.get_pending_tickets", new_callable=AsyncMock)
def test_process_pending_empty(mock_get_pending, mock_get_pool, client):
    mock_pool = AsyncMock()
    mock_get_pool.return_value = mock_pool
    mock_get_pending.return_value = []

    resp = client.post("/agent/process-pending")

    assert resp.status_code == 200
    data = resp.json()
    assert data["queued"] == 0
    assert data["ticket_ids"] == []
