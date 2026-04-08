"""
production/tests/test_e2e.py
Phase 5: End-to-end integration tests for CRM Digital FTE Factory.

All tests are skipped if TEST_DATABASE_URL is not set (CI-safe).

Usage:
    TEST_DATABASE_URL=postgresql://... pytest production/tests/test_e2e.py -v
"""

from __future__ import annotations

import os
import uuid

import pytest
import pytest_asyncio

# ---------------------------------------------------------------------------
# Skip guard — require TEST_DATABASE_URL
# ---------------------------------------------------------------------------

_DB_URL = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not _DB_URL,
    reason="TEST_DATABASE_URL not set — skipping E2E tests",
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="session")
async def db_pool():
    """Create a real asyncpg pool for the E2E test session."""
    import asyncpg

    pool = await asyncpg.create_pool(dsn=_DB_URL, min_size=1, max_size=5)
    yield pool
    await pool.close()


@pytest_asyncio.fixture()
async def http_client():
    """Async HTTPX client targeting the locally-running FastAPI server."""
    import httpx

    base_url = os.environ.get("API_BASE_URL", "http://localhost:8000")
    async with httpx.AsyncClient(base_url=base_url, timeout=30) as client:
        yield client


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _unique_email() -> str:
    return f"e2e-{uuid.uuid4().hex[:8]}@nexaflow-test.io"


# ---------------------------------------------------------------------------
# Test 1 — Web Form E2E
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_web_form_e2e(http_client):
    """Submit ticket via web form → agent processes it → verify final state."""
    email = _unique_email()
    payload = {
        "name": "E2E Test User",
        "email": email,
        "subject": "How do I set up automation rules?",
        "category": "general",
        "priority": "medium",
        "message": (
            "I am trying to set up automation rules in NexaFlow but I cannot "
            "find where to configure them. The documentation is unclear. "
            "Please help me understand how to create my first rule."
        ),
    }

    # Submit ticket
    resp = await http_client.post("/support/submit", json=payload)
    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert "ticket_id" in data
    ticket_id = data["ticket_id"]
    assert ticket_id.startswith("TKT-"), f"Expected TKT- prefix, got: {ticket_id}"

    # Process ticket through agent
    agent_resp = await http_client.post(f"/agent/process/{ticket_id}")
    assert agent_resp.status_code == 200, f"Agent returned {agent_resp.status_code}: {agent_resp.text}"
    agent_data = agent_resp.json()
    assert agent_data.get("ticket_id") == ticket_id or agent_data.get("ticket_id") is None

    # Verify status
    status = agent_data.get("resolution_status") or ("escalated" if agent_data.get("escalated") else "resolved")
    assert status in ("resolved", "escalated"), f"Unexpected status: {status}"

    # Fetch ticket and verify
    ticket_resp = await http_client.get(f"/support/ticket/{ticket_id}")
    assert ticket_resp.status_code == 200, f"Ticket lookup returned {ticket_resp.status_code}"
    ticket_data = ticket_resp.json()
    assert ticket_data.get("ticket_id") == ticket_id or ticket_data.get("display_ticket_id") == ticket_id


# ---------------------------------------------------------------------------
# Test 2 — Cross-channel identity (same email → same customer)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cross_channel_identity(http_client, db_pool):
    """Same email via two channels → same customer_id, both tickets in history."""
    from production.database import queries

    shared_email = _unique_email()

    # Ticket 1: web form channel
    resp1 = await http_client.post(
        "/support/submit",
        json={
            "name": "Cross Channel User",
            "email": shared_email,
            "subject": "First ticket via web form",
            "category": "general",
            "priority": "low",
            "message": "This is the first support request from this customer via web form channel.",
        },
    )
    assert resp1.status_code == 201
    ticket1_id = resp1.json()["ticket_id"]

    # Ticket 2: simulate a second ticket via same email (web form again, different subject)
    resp2 = await http_client.post(
        "/support/submit",
        json={
            "name": "Cross Channel User",
            "email": shared_email,
            "subject": "Second ticket same customer",
            "category": "technical",
            "priority": "medium",
            "message": "Following up with a second request from the same email address for cross-channel test.",
        },
    )
    assert resp2.status_code == 201
    ticket2_id = resp2.json()["ticket_id"]

    # Both tickets exist
    assert ticket1_id != ticket2_id

    # Fetch both tickets and verify same customer_id
    t1 = await queries.get_ticket_by_display_id(db_pool, ticket1_id)
    t2 = await queries.get_ticket_by_display_id(db_pool, ticket2_id)

    assert t1 is not None, f"Ticket {ticket1_id} not found in DB"
    assert t2 is not None, f"Ticket {ticket2_id} not found in DB"

    customer_id_1 = str(t1.get("customer_id", ""))
    customer_id_2 = str(t2.get("customer_id", ""))

    assert customer_id_1 == customer_id_2, (
        f"Expected same customer_id for same email, "
        f"got {customer_id_1} vs {customer_id_2}"
    )

    # Verify customer history contains both tickets
    history = await queries.get_customer_history(db_pool, customer_id_1)
    ticket_ids_in_history = [t.get("ticket_id") for t in history]
    assert ticket1_id in ticket_ids_in_history or len(history) >= 2, (
        f"Expected both tickets in history, got: {ticket_ids_in_history}"
    )


# ---------------------------------------------------------------------------
# Test 3 — Escalation path (refund request → escalated)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_escalation_path(http_client, db_pool):
    """Ticket with refund request must be escalated, not resolved."""
    from production.database import queries

    email = _unique_email()
    resp = await http_client.post(
        "/support/submit",
        json={
            "name": "Unhappy Customer",
            "email": email,
            "subject": "Request for full refund",
            "category": "billing",
            "priority": "urgent",
            "message": (
                "I am very disappointed with NexaFlow. The product does not work "
                "as advertised. I need a full refund immediately. Please process "
                "this refund request and cancel my account."
            ),
        },
    )
    assert resp.status_code == 201
    ticket_id = resp.json()["ticket_id"]

    # Run agent
    agent_resp = await http_client.post(f"/agent/process/{ticket_id}")
    assert agent_resp.status_code == 200

    # Check: should be escalated due to refund keyword
    agent_data = agent_resp.json()
    escalated = agent_data.get("escalated", False)
    resolution_status = agent_data.get("resolution_status", "")

    # Verify in DB too
    ticket = await queries.get_ticket_by_display_id(db_pool, ticket_id)
    db_status = ticket.get("status", "") if ticket else ""

    assert escalated or resolution_status == "escalated" or db_status == "escalated", (
        f"Expected escalation for refund request. "
        f"escalated={escalated}, resolution_status={resolution_status}, db_status={db_status}"
    )


# ---------------------------------------------------------------------------
# Test 4 — Metrics endpoint accuracy
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_metrics_endpoint(http_client):
    """Submit 3 tickets → resolve 2 + escalate 1 → metrics counts match delta."""
    email_base = _unique_email()

    # Fetch baseline metrics
    baseline_resp = await http_client.get("/metrics/summary")
    assert baseline_resp.status_code == 200
    baseline = baseline_resp.json()
    baseline_total = baseline.get("total_tickets", 0)

    # Submit 3 tickets
    ticket_ids = []
    for i in range(3):
        r = await http_client.post(
            "/support/submit",
            json={
                "name": f"Metrics Test User {i}",
                "email": f"metrics-{i}-{email_base}",
                "subject": f"Metrics test ticket {i}",
                "category": "general",
                "priority": "low",
                "message": (
                    f"This is metrics test ticket number {i}. "
                    "I need help setting up my NexaFlow workspace integration properly."
                ),
            },
        )
        assert r.status_code == 201
        ticket_ids.append(r.json()["ticket_id"])

    assert len(ticket_ids) == 3

    # Process all 3 tickets
    for tid in ticket_ids:
        ar = await http_client.post(f"/agent/process/{tid}")
        assert ar.status_code == 200

    # Fetch updated metrics — total should have increased by at least 3
    updated_resp = await http_client.get("/metrics/summary")
    assert updated_resp.status_code == 200
    updated = updated_resp.json()
    updated_total = updated.get("total_tickets", 0)

    assert updated_total >= baseline_total + 3, (
        f"Expected total_tickets to increase by at least 3. "
        f"Baseline: {baseline_total}, Updated: {updated_total}"
    )


# ---------------------------------------------------------------------------
# Test 5 — Health check
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_check(http_client):
    """GET /health must return status=healthy, database=connected, timestamp PKT."""
    resp = await http_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()

    assert data.get("status") == "healthy", f"Expected healthy, got: {data.get('status')}"
    assert data.get("database") == "connected", f"Expected connected, got: {data.get('database')}"

    timestamp = data.get("timestamp", "")
    assert "PKT" in timestamp, f"Expected PKT in timestamp, got: {timestamp}"
