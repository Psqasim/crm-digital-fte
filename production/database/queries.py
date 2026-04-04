"""
production/database/queries.py
Phase 4A: Async database query functions using asyncpg.

All functions:
- Use async/await (asyncpg native)
- Accept pool as injectable parameter (ADR-0001 pattern)
- Log errors to stderr via logging module
- Never raise naked exceptions to caller; return None/[] on failure
"""

from __future__ import annotations

import logging
import os
from typing import Any

import asyncpg

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Connection pool
# ---------------------------------------------------------------------------

_pool: asyncpg.Pool | None = None


async def get_db_pool() -> asyncpg.Pool:
    """Return (or lazily create) the global asyncpg connection pool.

    Reads DATABASE_URL from environment.  Neon format:
        postgresql://user:password@host/dbname?sslmode=require
    """
    global _pool
    if _pool is None:
        database_url = os.environ["DATABASE_URL"]
        _pool = await asyncpg.create_pool(
            dsn=database_url,
            min_size=2,
            max_size=10,
            command_timeout=30,
            max_inactive_connection_lifetime=300.0,
        )
    return _pool


# ---------------------------------------------------------------------------
# Customer helpers
# ---------------------------------------------------------------------------


async def get_or_create_customer(
    pool: asyncpg.Pool,
    email: str,
    name: str | None = None,
) -> dict[str, Any] | None:
    """Return existing customer by email or create a new one.

    Idempotent — calling twice with the same email returns the same record.
    If the customer exists but name is provided, updates the name.
    """
    try:
        async with pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    "SELECT id, email, name, created_at, updated_at, metadata "
                    "FROM customers WHERE email = $1",
                    email,
                )
                if row:
                    if name and row["name"] != name:
                        row = await conn.fetchrow(
                            "UPDATE customers SET name = $1, updated_at = NOW() "
                            "WHERE email = $2 "
                            "RETURNING id, email, name, created_at, updated_at, metadata",
                            name,
                            email,
                        )
                    return dict(row)

                row = await conn.fetchrow(
                    "INSERT INTO customers (email, name) "
                    "VALUES ($1, $2) "
                    "RETURNING id, email, name, created_at, updated_at, metadata",
                    email,
                    name,
                )
                return dict(row)
    except Exception:
        logger.exception("get_or_create_customer failed for email=%s", email)
        return None


async def resolve_phone_to_customer(
    pool: asyncpg.Pool,
    phone: str,
) -> str | None:
    """Return customer_id (UUID str) for a given phone number, or None."""
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT customer_id FROM customer_identifiers "
                "WHERE identifier_type = 'phone' AND identifier_value = $1",
                phone,
            )
            return str(row["customer_id"]) if row else None
    except Exception:
        logger.exception("resolve_phone_to_customer failed for phone=%s", phone)
        return None


async def link_phone_to_customer(
    pool: asyncpg.Pool,
    customer_id: str,
    phone: str,
) -> None:
    """Link a phone number to a customer (upsert — no-op if already linked)."""
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO customer_identifiers "
                "  (customer_id, identifier_type, identifier_value) "
                "VALUES ($1, 'phone', $2) "
                "ON CONFLICT (identifier_type, identifier_value) DO NOTHING",
                customer_id,
                phone,
            )
    except Exception:
        logger.exception(
            "link_phone_to_customer failed for customer_id=%s phone=%s",
            customer_id,
            phone,
        )


# ---------------------------------------------------------------------------
# Conversation / message helpers
# ---------------------------------------------------------------------------


async def create_conversation(
    pool: asyncpg.Pool,
    customer_id: str,
    channel: str,
) -> str | None:
    """Create a new conversation and return its UUID string."""
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "INSERT INTO conversations (customer_id, channel) "
                "VALUES ($1, $2) "
                "RETURNING id",
                customer_id,
                channel,
            )
            return str(row["id"])
    except Exception:
        logger.exception(
            "create_conversation failed for customer_id=%s channel=%s",
            customer_id,
            channel,
        )
        return None


async def add_message(
    pool: asyncpg.Pool,
    conversation_id: str,
    role: str,
    content: str,
    channel: str,
    sentiment_score: float | None = None,
) -> str | None:
    """Append a message to a conversation and return the message UUID string."""
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "INSERT INTO messages "
                "  (conversation_id, role, content, channel, sentiment_score) "
                "VALUES ($1, $2, $3, $4, $5) "
                "RETURNING id",
                conversation_id,
                role,
                content,
                channel,
                sentiment_score,
            )
            await conn.execute(
                "UPDATE conversations SET updated_at = NOW() WHERE id = $1",
                conversation_id,
            )
            return str(row["id"])
    except Exception:
        logger.exception(
            "add_message failed for conversation_id=%s role=%s",
            conversation_id,
            role,
        )
        return None


async def get_customer_history(
    pool: asyncpg.Pool,
    customer_id: str,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Return the most recent conversations with their messages for a customer.

    Each item: {conversation_id, channel, status, started_at, messages: [...]}
    """
    try:
        async with pool.acquire() as conn:
            conv_rows = await conn.fetch(
                "SELECT id, channel, status, started_at, updated_at "
                "FROM conversations "
                "WHERE customer_id = $1 "
                "ORDER BY started_at DESC "
                "LIMIT $2",
                customer_id,
                limit,
            )
            result: list[dict[str, Any]] = []
            for conv in conv_rows:
                msg_rows = await conn.fetch(
                    "SELECT id, role, content, channel, sentiment_score, created_at "
                    "FROM messages "
                    "WHERE conversation_id = $1 "
                    "ORDER BY created_at ASC",
                    str(conv["id"]),
                )
                result.append(
                    {
                        "conversation_id": str(conv["id"]),
                        "channel": conv["channel"],
                        "status": conv["status"],
                        "started_at": conv["started_at"],
                        "updated_at": conv["updated_at"],
                        "messages": [dict(m) for m in msg_rows],
                    }
                )
            return result
    except Exception:
        logger.exception(
            "get_customer_history failed for customer_id=%s", customer_id
        )
        return []


async def get_sentiment_trend(
    pool: asyncpg.Pool,
    customer_id: str,
    last_n: int = 5,
) -> list[float]:
    """Return the last N sentiment scores for a customer (most-recent first)."""
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT m.sentiment_score "
                "FROM messages m "
                "JOIN conversations c ON c.id = m.conversation_id "
                "WHERE c.customer_id = $1 "
                "  AND m.sentiment_score IS NOT NULL "
                "  AND m.role = 'customer' "
                "ORDER BY m.created_at DESC "
                "LIMIT $2",
                customer_id,
                last_n,
            )
            return [row["sentiment_score"] for row in rows]
    except Exception:
        logger.exception(
            "get_sentiment_trend failed for customer_id=%s", customer_id
        )
        return []


# ---------------------------------------------------------------------------
# Ticket helpers
# ---------------------------------------------------------------------------


async def create_ticket(
    pool: asyncpg.Pool,
    conversation_id: str,
    customer_id: str,
    channel: str,
    subject: str | None = None,
    category: str | None = None,
) -> str | None:
    """Create a support ticket and return its UUID string."""
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "INSERT INTO tickets "
                "  (conversation_id, customer_id, channel, subject, category) "
                "VALUES ($1, $2, $3, $4, $5) "
                "RETURNING id",
                conversation_id,
                customer_id,
                channel,
                subject,
                category,
            )
            return str(row["id"])
    except Exception:
        logger.exception(
            "create_ticket failed for conversation_id=%s", conversation_id
        )
        return None


async def update_ticket_status(
    pool: asyncpg.Pool,
    ticket_id: str,
    status: str,
    reason: str | None = None,
) -> None:
    """Update ticket status and optionally set escalation_reason or resolution_summary."""
    try:
        async with pool.acquire() as conn:
            if status == "resolved":
                await conn.execute(
                    "UPDATE tickets "
                    "SET status = $1, resolution_summary = $2, "
                    "    resolved_at = NOW(), updated_at = NOW() "
                    "WHERE id = $3",
                    status,
                    reason,
                    ticket_id,
                )
            elif status == "escalated":
                await conn.execute(
                    "UPDATE tickets "
                    "SET status = $1, escalation_reason = $2, updated_at = NOW() "
                    "WHERE id = $3",
                    status,
                    reason,
                    ticket_id,
                )
            else:
                await conn.execute(
                    "UPDATE tickets SET status = $1, updated_at = NOW() WHERE id = $2",
                    status,
                    ticket_id,
                )
    except Exception:
        logger.exception(
            "update_ticket_status failed for ticket_id=%s status=%s",
            ticket_id,
            status,
        )


# ---------------------------------------------------------------------------
# Knowledge base helpers
# ---------------------------------------------------------------------------


async def search_knowledge_base(
    pool: asyncpg.Pool,
    embedding: list[float],
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Cosine similarity search over knowledge_base using pgvector.

    Returns up to `limit` results sorted by similarity descending.
    embedding must be a list of 1536 floats (text-embedding-3-small).
    """
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, title, content, category, "
                "       1 - (embedding <=> $1::vector) AS similarity "
                "FROM knowledge_base "
                "WHERE embedding IS NOT NULL "
                "ORDER BY embedding <=> $1::vector "
                "LIMIT $2",
                embedding,
                limit,
            )
            return [dict(r) for r in rows]
    except Exception:
        logger.exception("search_knowledge_base failed")
        return []


async def upsert_knowledge_base(
    pool: asyncpg.Pool,
    title: str,
    content: str,
    category: str | None,
    embedding: list[float],
) -> str | None:
    """Insert or update a knowledge base chunk; return its UUID string.

    Matches on title+category. Updates content+embedding if already present.
    """
    try:
        async with pool.acquire() as conn:
            async with conn.transaction():
                existing = await conn.fetchrow(
                    "SELECT id FROM knowledge_base "
                    "WHERE title = $1 AND category IS NOT DISTINCT FROM $2",
                    title,
                    category,
                )
                if existing:
                    await conn.execute(
                        "UPDATE knowledge_base "
                        "SET content = $1, embedding = $2::vector, updated_at = NOW() "
                        "WHERE id = $3",
                        content,
                        embedding,
                        existing["id"],
                    )
                    return str(existing["id"])

                row = await conn.fetchrow(
                    "INSERT INTO knowledge_base (title, content, category, embedding) "
                    "VALUES ($1, $2, $3, $4::vector) "
                    "RETURNING id",
                    title,
                    content,
                    category,
                    embedding,
                )
                return str(row["id"])
    except Exception:
        logger.exception("upsert_knowledge_base failed for title=%s", title)
        return None


# ---------------------------------------------------------------------------
# Metrics helper
# ---------------------------------------------------------------------------


async def record_metric(
    pool: asyncpg.Pool,
    metric_name: str,
    value: float,
    channel: str | None = None,
) -> None:
    """Append an operational metric data point."""
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO agent_metrics (metric_name, metric_value, channel) "
                "VALUES ($1, $2, $3)",
                metric_name,
                value,
                channel,
            )
    except Exception:
        logger.exception(
            "record_metric failed for metric_name=%s", metric_name
        )
