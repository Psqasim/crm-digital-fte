"""
production/tests/test_database.py
Phase 4A: Integration tests for production/database/queries.py

All tests require a live PostgreSQL database.
Set TEST_DATABASE_URL in environment to run; skip gracefully if not set.

Run:
    TEST_DATABASE_URL=postgresql://... pytest production/tests/test_database.py -v
"""

from __future__ import annotations

import os
import uuid

import asyncpg
import pytest
import pytest_asyncio

# ---------------------------------------------------------------------------
# Skip guard — all tests skip if TEST_DATABASE_URL is not set
# ---------------------------------------------------------------------------
pytestmark = pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set — skipping database integration tests",
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="session")
async def pool():
    """Session-scoped asyncpg pool connected to the test database."""
    test_url = os.environ["TEST_DATABASE_URL"]
    p = await asyncpg.create_pool(dsn=test_url, min_size=1, max_size=5)
    yield p
    await p.close()


@pytest_asyncio.fixture(autouse=True)
async def clean_tables(pool):
    """Truncate test data tables before each test (cascade)."""
    async with pool.acquire() as conn:
        await conn.execute(
            "TRUNCATE TABLE agent_metrics, tickets, messages, "
            "conversations, customer_identifiers, knowledge_base, customers "
            "RESTART IDENTITY CASCADE"
        )
    yield


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _unique_email() -> str:
    return f"test_{uuid.uuid4().hex[:8]}@example.com"


def _fake_embedding(value: float = 0.1) -> list[float]:
    """Return a 1536-dim embedding filled with a constant value."""
    return [value] * 1536


# ---------------------------------------------------------------------------
# Tests: get_or_create_customer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_or_create_customer_creates_new(pool):
    from production.database.queries import get_or_create_customer

    email = _unique_email()
    customer = await get_or_create_customer(pool, email=email, name="Alice Test")

    assert customer is not None
    assert customer["email"] == email
    assert customer["name"] == "Alice Test"
    assert "id" in customer


@pytest.mark.asyncio
async def test_get_or_create_customer_idempotent(pool):
    """Calling twice with the same email returns the same record."""
    from production.database.queries import get_or_create_customer

    email = _unique_email()
    c1 = await get_or_create_customer(pool, email=email, name="Bob Test")
    c2 = await get_or_create_customer(pool, email=email, name="Bob Test")

    assert c1 is not None
    assert c2 is not None
    assert c1["id"] == c2["id"]
    assert c1["email"] == c2["email"]


@pytest.mark.asyncio
async def test_get_or_create_customer_updates_name(pool):
    """If name changes on second call, the record is updated."""
    from production.database.queries import get_or_create_customer

    email = _unique_email()
    await get_or_create_customer(pool, email=email, name="Old Name")
    updated = await get_or_create_customer(pool, email=email, name="New Name")

    assert updated is not None
    assert updated["name"] == "New Name"


# ---------------------------------------------------------------------------
# Tests: resolve_phone_to_customer / link_phone_to_customer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_phone_not_found(pool):
    """Returns None when phone is not linked to any customer."""
    from production.database.queries import resolve_phone_to_customer

    result = await resolve_phone_to_customer(pool, phone="+10000000000")
    assert result is None


@pytest.mark.asyncio
async def test_link_then_resolve_phone(pool):
    """Link a phone to a customer, then resolve it back."""
    from production.database.queries import (
        get_or_create_customer,
        link_phone_to_customer,
        resolve_phone_to_customer,
    )

    email = _unique_email()
    customer = await get_or_create_customer(pool, email=email, name="Charlie")
    assert customer is not None

    phone = f"+1555{uuid.uuid4().int % 10_000_000:07d}"
    await link_phone_to_customer(pool, customer_id=str(customer["id"]), phone=phone)

    resolved = await resolve_phone_to_customer(pool, phone=phone)
    assert resolved == str(customer["id"])


@pytest.mark.asyncio
async def test_link_phone_idempotent(pool):
    """Linking the same phone twice does not raise an error."""
    from production.database.queries import (
        get_or_create_customer,
        link_phone_to_customer,
        resolve_phone_to_customer,
    )

    email = _unique_email()
    customer = await get_or_create_customer(pool, email=email)
    assert customer is not None

    phone = f"+1555{uuid.uuid4().int % 10_000_000:07d}"
    await link_phone_to_customer(pool, customer_id=str(customer["id"]), phone=phone)
    await link_phone_to_customer(pool, customer_id=str(customer["id"]), phone=phone)

    resolved = await resolve_phone_to_customer(pool, phone=phone)
    assert resolved == str(customer["id"])


# ---------------------------------------------------------------------------
# Tests: create_conversation + add_message + get_customer_history
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_conversation(pool):
    from production.database.queries import create_conversation, get_or_create_customer

    email = _unique_email()
    customer = await get_or_create_customer(pool, email=email)
    assert customer is not None

    conv_id = await create_conversation(pool, customer_id=str(customer["id"]), channel="email")
    assert conv_id is not None
    assert len(conv_id) == 36  # UUID format


@pytest.mark.asyncio
async def test_add_message_and_get_history(pool):
    from production.database.queries import (
        add_message,
        create_conversation,
        get_customer_history,
        get_or_create_customer,
    )

    email = _unique_email()
    customer = await get_or_create_customer(pool, email=email, name="Diana")
    assert customer is not None
    customer_id = str(customer["id"])

    conv_id = await create_conversation(pool, customer_id=customer_id, channel="web_form")
    assert conv_id is not None

    msg1 = await add_message(
        pool,
        conversation_id=conv_id,
        role="customer",
        content="Hello, I need help.",
        channel="web_form",
        sentiment_score=-0.2,
    )
    msg2 = await add_message(
        pool,
        conversation_id=conv_id,
        role="agent",
        content="Hi Diana, I'm here to help!",
        channel="web_form",
    )

    assert msg1 is not None
    assert msg2 is not None

    history = await get_customer_history(pool, customer_id=customer_id)
    assert len(history) == 1
    assert history[0]["channel"] == "web_form"
    assert len(history[0]["messages"]) == 2
    assert history[0]["messages"][0]["role"] == "customer"
    assert history[0]["messages"][1]["role"] == "agent"


# ---------------------------------------------------------------------------
# Tests: update_ticket_status
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_ticket_status_transitions(pool):
    from production.database.queries import (
        create_conversation,
        create_ticket,
        get_or_create_customer,
        update_ticket_status,
    )

    email = _unique_email()
    customer = await get_or_create_customer(pool, email=email)
    assert customer is not None
    customer_id = str(customer["id"])

    conv_id = await create_conversation(pool, customer_id=customer_id, channel="email")
    ticket_id = await create_ticket(
        pool,
        conversation_id=conv_id,
        customer_id=customer_id,
        channel="email",
        subject="Test ticket",
        category="billing",
    )
    assert ticket_id is not None

    # open → escalated
    await update_ticket_status(pool, ticket_id=ticket_id, status="escalated", reason="Refund request")

    # escalated → resolved
    await update_ticket_status(pool, ticket_id=ticket_id, status="resolved", reason="Refund processed")

    # Verify final state directly
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT status, escalation_reason, resolution_summary, resolved_at "
            "FROM tickets WHERE id = $1",
            ticket_id,
        )
    assert row["status"] == "resolved"
    assert row["escalation_reason"] == "Refund request"
    assert row["resolution_summary"] == "Refund processed"
    assert row["resolved_at"] is not None


@pytest.mark.asyncio
async def test_update_ticket_status_pending(pool):
    from production.database.queries import (
        create_conversation,
        create_ticket,
        get_or_create_customer,
        update_ticket_status,
    )

    email = _unique_email()
    customer = await get_or_create_customer(pool, email=email)
    assert customer is not None
    customer_id = str(customer["id"])

    conv_id = await create_conversation(pool, customer_id=customer_id, channel="whatsapp")
    ticket_id = await create_ticket(
        pool,
        conversation_id=conv_id,
        customer_id=customer_id,
        channel="whatsapp",
    )
    assert ticket_id is not None

    await update_ticket_status(pool, ticket_id=ticket_id, status="pending")

    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT status FROM tickets WHERE id = $1", ticket_id)
    assert row["status"] == "pending"


# ---------------------------------------------------------------------------
# Tests: record_metric
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_record_metric(pool):
    from production.database.queries import record_metric

    await record_metric(pool, metric_name="tickets_processed", value=1.0, channel="email")
    await record_metric(pool, metric_name="escalation_rate", value=0.15)

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT metric_name, metric_value, channel FROM agent_metrics ORDER BY recorded_at"
        )
    assert len(rows) == 2
    assert rows[0]["metric_name"] == "tickets_processed"
    assert rows[0]["channel"] == "email"
    assert rows[1]["metric_name"] == "escalation_rate"
    assert rows[1]["channel"] is None
