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
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import asyncpg

logger = logging.getLogger(__name__)


def _serialize_row(row) -> dict:
    """Convert an asyncpg Record to a plain dict, serializing UUIDs and datetimes to str."""
    return {
        k: str(v) if hasattr(v, "hex") or hasattr(v, "isoformat") else v
        for k, v in dict(row).items()
    }

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
# WhatsApp message deduplication (cross-worker safe)
# ---------------------------------------------------------------------------


async def claim_whatsapp_message(pool: asyncpg.Pool, message_sid: str) -> bool:
    """Atomically claim a Twilio MessageSid so only one worker processes it.

    Creates the whatsapp_message_log table on first call (idempotent).
    Returns True if this worker claimed it (process the message).
    Returns False if another worker already claimed it (skip).
    """
    try:
        async with pool.acquire() as conn:
            # Create table if not exists (safe to call every time — very cheap)
            await conn.execute(
                "CREATE TABLE IF NOT EXISTS whatsapp_message_log ("
                "  message_sid TEXT PRIMARY KEY, "
                "  claimed_at TIMESTAMPTZ DEFAULT NOW()"
                ")"
            )
            # Try to insert — fails silently if already exists
            result = await conn.execute(
                "INSERT INTO whatsapp_message_log (message_sid) "
                "VALUES ($1) ON CONFLICT (message_sid) DO NOTHING",
                message_sid,
            )
            # INSERT returns 'INSERT 0 N' — N=1 means we inserted, N=0 means duplicate
            return result == "INSERT 0 1"
    except Exception:
        logger.exception("claim_whatsapp_message failed for sid=%s — allowing processing", message_sid)
        # On DB error, allow processing (better to duplicate than to silently drop)
        return True


# ---------------------------------------------------------------------------
# Gmail message deduplication (cross-worker safe)
# ---------------------------------------------------------------------------


async def claim_gmail_message(pool: asyncpg.Pool, message_id: str) -> bool:
    """Atomically claim a Gmail message ID so only one worker processes it.

    Creates the gmail_message_log table on first call (idempotent).
    Returns True if this worker claimed it (process the message).
    Returns False if another worker already claimed it (skip).
    """
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                "CREATE TABLE IF NOT EXISTS gmail_message_log ("
                "  message_id TEXT PRIMARY KEY, "
                "  claimed_at TIMESTAMPTZ DEFAULT NOW()"
                ")"
            )
            result = await conn.execute(
                "INSERT INTO gmail_message_log (message_id) "
                "VALUES ($1) ON CONFLICT (message_id) DO NOTHING",
                message_id,
            )
            return result == "INSERT 0 1"
    except Exception:
        logger.exception("claim_gmail_message failed for id=%s — allowing processing", message_id)
        return True


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
                        "started_at": str(conv["started_at"]) if conv["started_at"] else None,
                        "updated_at": str(conv["updated_at"]) if conv["updated_at"] else None,
                        "messages": [_serialize_row(m) for m in msg_rows],
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
    priority: str = "medium",
) -> str | None:
    """Create a support ticket and return its UUID string."""
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "INSERT INTO tickets "
                "  (conversation_id, customer_id, channel, subject, category, priority) "
                "VALUES ($1, $2, $3, $4, $5, $6) "
                "RETURNING id, priority",
                conversation_id,
                customer_id,
                channel,
                subject,
                category,
                priority,
            )
            return str(row["id"])
    except Exception:
        logger.exception(
            "create_ticket failed for conversation_id=%s", conversation_id
        )
        return None


async def get_ticket_by_display_id(
    pool: asyncpg.Pool,
    ticket_id: str,
) -> dict[str, Any] | None:
    """Return full ticket dict by display ID (TKT-XXXXXXXX) or raw UUID string.

    Returns dict with 13 fields or None if not found.
    """
    try:
        async with pool.acquire() as conn:
            if ticket_id.startswith("TKT-"):
                suffix = ticket_id[4:].upper()
                row = await conn.fetchrow(
                    "SELECT t.id, t.conversation_id, t.customer_id, "
                    "       t.status, t.category, t.priority, t.subject, t.channel, "
                    "       t.created_at, t.updated_at, t.resolved_at, "
                    "       c.name AS customer_name, c.email AS customer_email, "
                    "       cust_msg.content AS body "
                    "FROM tickets t "
                    "JOIN customers c ON c.id = t.customer_id "
                    "LEFT JOIN LATERAL ("
                    "  SELECT content FROM messages "
                    "  WHERE conversation_id = t.conversation_id AND role = 'customer' "
                    "  ORDER BY created_at ASC LIMIT 1"
                    ") cust_msg ON true "
                    "WHERE upper(substring(t.id::text, 1, 8)) = $1 "
                    "LIMIT 1",
                    suffix,
                )
            else:
                row = await conn.fetchrow(
                    "SELECT t.id, t.conversation_id, t.customer_id, "
                    "       t.status, t.category, t.priority, t.subject, t.channel, "
                    "       t.created_at, t.updated_at, t.resolved_at, "
                    "       c.name AS customer_name, c.email AS customer_email, "
                    "       cust_msg.content AS body "
                    "FROM tickets t "
                    "JOIN customers c ON c.id = t.customer_id "
                    "LEFT JOIN LATERAL ("
                    "  SELECT content FROM messages "
                    "  WHERE conversation_id = t.conversation_id AND role = 'customer' "
                    "  ORDER BY created_at ASC LIMIT 1"
                    ") cust_msg ON true "
                    "WHERE t.id::text = $1 "
                    "LIMIT 1",
                    ticket_id,
                )
            if row is None:
                return None
            internal_id = str(row["id"])
            display_id = "TKT-" + internal_id[:8].upper()
            conv_id = str(row["conversation_id"]) if row["conversation_id"] else None

            # Fetch all messages for this conversation (customer, AI, human agent)
            ai_response: str | None = None
            messages: list[dict[str, Any]] = []
            if conv_id:
                msg_rows = await conn.fetch(
                    "SELECT role, content, created_at FROM messages "
                    "WHERE conversation_id = $1 "
                    "ORDER BY created_at ASC",
                    row["conversation_id"],
                )
                for m in msg_rows:
                    messages.append({
                        "role": m["role"],
                        "content": m["content"],
                        "created_at": m["created_at"].isoformat() if hasattr(m["created_at"], "isoformat") else str(m["created_at"]),
                        "is_human_agent": m["role"] == "agent",
                    })
                # Latest assistant message kept for backward compat
                for m in reversed(messages):
                    if m["role"] == "assistant":
                        ai_response = m["content"]
                        break

            return {
                "ticket_id": display_id,
                "internal_id": internal_id,
                "conversation_id": conv_id,
                "customer_id": str(row["customer_id"]) if row["customer_id"] else None,
                "status": row["status"],
                "category": row["category"],
                "priority": row["priority"],
                "subject": row["subject"],
                "channel": row["channel"],
                "message": row["body"],
                "ai_response": ai_response,
                "messages": messages,
                "customer_name": row["customer_name"],
                "customer_email": row["customer_email"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "resolved_at": row["resolved_at"],
            }
    except Exception:
        logger.exception("get_ticket_by_display_id failed for ticket_id=%s", ticket_id)
        return None


async def get_metrics_summary(
    pool: asyncpg.Pool,
) -> dict[str, Any]:
    """Return aggregated ticket metrics for the dashboard.

    Returns dict matching contracts/web-form-api.md MetricsSummary shape.
    Includes: counts, escalation_rate_percent, avg_resolution_time_minutes,
    tickets_last_24h, top_categories, channel_breakdown, recent_tickets.
    """
    try:
        async with pool.acquire() as conn:
            counts_row = await conn.fetchrow(
                "SELECT "
                "  COUNT(*) AS total, "
                "  COUNT(*) FILTER (WHERE status = 'open') AS open, "
                "  COUNT(*) FILTER (WHERE status = 'in_progress') AS in_progress, "
                "  COUNT(*) FILTER (WHERE status = 'resolved') AS resolved, "
                "  COUNT(*) FILTER (WHERE status = 'escalated') AS escalated, "
                "  COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours') AS last_24h, "
                "  ROUND(EXTRACT(EPOCH FROM AVG(resolved_at - created_at)) / 60, 1) "
                "    AS avg_resolution_minutes "
                "FROM tickets"
            )
            total = int(counts_row["total"])
            open_ = int(counts_row["open"])
            in_progress = int(counts_row["in_progress"])
            resolved = int(counts_row["resolved"])
            escalated = int(counts_row["escalated"])
            last_24h = int(counts_row["last_24h"])
            escalation_rate = round((escalated / total) * 100, 1) if total > 0 else 0.0
            avg_resolution = float(counts_row["avg_resolution_minutes"] or 0.0)

            channel_rows = await conn.fetch(
                "SELECT channel, COUNT(*) AS cnt FROM tickets GROUP BY channel"
            )
            channels: dict[str, int] = {r["channel"]: int(r["cnt"]) for r in channel_rows}

            category_rows = await conn.fetch(
                "SELECT category, COUNT(*) AS cnt "
                "FROM tickets "
                "WHERE category IS NOT NULL "
                "GROUP BY category "
                "ORDER BY cnt DESC "
                "LIMIT 3"
            )
            top_categories = [
                {"category": r["category"], "count": int(r["cnt"])}
                for r in category_rows
            ]

            recent_rows = await conn.fetch(
                "SELECT t.id, t.status, t.category, t.priority, t.subject, "
                "       t.created_at, c.name AS customer_name "
                "FROM tickets t "
                "JOIN customers c ON c.id = t.customer_id "
                "ORDER BY t.created_at DESC "
                "LIMIT 10"
            )
            recent_tickets = [
                {
                    "ticket_id": "TKT-" + str(r["id"])[:8].upper(),
                    "status": r["status"],
                    "category": r["category"],
                    "priority": r["priority"],
                    "subject": r["subject"],
                    "created_at": r["created_at"],
                    "customer_name": r["customer_name"],
                }
                for r in recent_rows
            ]

            return {
                "total": total,
                "open": open_,
                "in_progress": in_progress,
                "resolved": resolved,
                "escalated": escalated,
                "escalation_rate": escalation_rate,
                "escalation_rate_percent": escalation_rate,
                "avg_resolution_time_minutes": avg_resolution,
                "tickets_last_24h": last_24h,
                "top_categories": top_categories,
                "channel_breakdown": channels,
                "channels": channels,
                "recent_tickets": recent_tickets,
            }
    except Exception:
        logger.exception("get_metrics_summary failed")
        return {
            "total": 0,
            "open": 0,
            "in_progress": 0,
            "resolved": 0,
            "escalated": 0,
            "escalation_rate": 0.0,
            "escalation_rate_percent": 0.0,
            "avg_resolution_time_minutes": 0.0,
            "tickets_last_24h": 0,
            "top_categories": [],
            "channel_breakdown": {},
            "channels": {},
            "recent_tickets": [],
        }


async def get_tickets_by_email(
    pool: asyncpg.Pool,
    email: str,
) -> list[dict]:
    """Return tickets submitted by a customer with the given email address.

    Returns list of dicts with ticket_id, status, category, priority, subject,
    created_at, updated_at — sorted newest first.
    """
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT t.id, t.status, t.category, t.priority, t.subject, "
                "       t.channel, t.created_at, t.updated_at "
                "FROM tickets t "
                "JOIN customers c ON c.id = t.customer_id "
                "WHERE c.email = $1 "
                "ORDER BY t.created_at DESC "
                "LIMIT 50",
                email.lower(),
            )
            return [
                {
                    "ticket_id": "TKT-" + str(r["id"])[:8].upper(),
                    "status": r["status"],
                    "category": r["category"],
                    "priority": r["priority"],
                    "subject": r["subject"],
                    "channel": r["channel"],
                    "created_at": r["created_at"].isoformat() if hasattr(r["created_at"], "isoformat") else r["created_at"],
                    "updated_at": r["updated_at"].isoformat() if r["updated_at"] and hasattr(r["updated_at"], "isoformat") else r["updated_at"],
                }
                for r in rows
            ]
    except Exception:
        logger.exception("get_tickets_by_email failed for email=%s", email)
        return []


async def get_channel_metrics(
    pool: asyncpg.Pool,
) -> dict[str, Any]:
    """Return per-channel ticket metrics.

    Returns dict keyed by channel with total/open/resolved/avg_resolution_min.
    """
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT "
                "  channel, "
                "  COUNT(*) AS total, "
                "  COUNT(*) FILTER (WHERE status = 'open') AS open, "
                "  COUNT(*) FILTER (WHERE status = 'resolved') AS resolved, "
                "  ROUND(EXTRACT(EPOCH FROM AVG(resolved_at - created_at)) / 60, 1) "
                "    AS avg_resolution_min "
                "FROM tickets "
                "GROUP BY channel"
            )
            result: dict[str, Any] = {}
            for r in rows:
                result[r["channel"]] = {
                    "total": int(r["total"]),
                    "open": int(r["open"]),
                    "resolved": int(r["resolved"]),
                    "avg_resolution_min": float(r["avg_resolution_min"] or 0.0),
                }
            # Ensure standard channels always present even if no tickets yet
            for ch in ("email", "whatsapp", "web_form"):
                if ch not in result:
                    result[ch] = {"total": 0, "open": 0, "resolved": 0, "avg_resolution_min": 0.0}
            return result
    except Exception:
        logger.exception("get_channel_metrics failed")
        return {
            ch: {"total": 0, "open": 0, "resolved": 0, "avg_resolution_min": 0.0}
            for ch in ("email", "whatsapp", "web_form")
        }


async def update_ticket_status(
    pool: asyncpg.Pool,
    ticket_id: str,
    status: str,
    reason: str | None = None,
) -> None:
    """Update ticket status and optionally set escalation_reason or resolution_summary.

    ticket_id may be either an internal UUID string or a display ID (TKT-XXXXXXXX).
    Display IDs are resolved to the internal UUID before updating.
    """
    try:
        async with pool.acquire() as conn:
            # Resolve display ID → internal UUID if needed
            internal_id = ticket_id
            if ticket_id.startswith("TKT-"):
                suffix = ticket_id[4:].upper()
                row = await conn.fetchrow(
                    "SELECT id::text FROM tickets "
                    "WHERE upper(substring(id::text, 1, 8)) = $1 LIMIT 1",
                    suffix,
                )
                if not row:
                    logger.warning(
                        "update_ticket_status: display ID %s not found", ticket_id
                    )
                    return
                internal_id = row[0]

            if status == "resolved":
                await conn.execute(
                    "UPDATE tickets "
                    "SET status = $1, resolution_summary = $2, "
                    "    resolved_at = NOW(), updated_at = NOW() "
                    "WHERE id = $3::uuid",
                    status,
                    reason,
                    internal_id,
                )
            elif status == "escalated":
                await conn.execute(
                    "UPDATE tickets "
                    "SET status = $1, escalation_reason = $2, updated_at = NOW() "
                    "WHERE id = $3::uuid",
                    status,
                    reason,
                    internal_id,
                )
            else:
                await conn.execute(
                    "UPDATE tickets SET status = $1, updated_at = NOW() "
                    "WHERE id = $2::uuid",
                    status,
                    internal_id,
                )
    except Exception:
        logger.exception(
            "update_ticket_status failed for ticket_id=%s status=%s",
            ticket_id,
            status,
        )


async def get_pending_tickets(
    pool: asyncpg.Pool,
    statuses: tuple[str, ...] = ("open", "pending"),
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Return tickets with the given statuses (default: open, pending).

    Each item contains ticket_id (TKT-XXXXXXXX), internal_id, status, channel,
    conversation_id, customer_id, customer_name, customer_email, and message.
    """
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT t.id, t.conversation_id, t.customer_id, t.status, "
                "       t.channel, t.subject, "
                "       c.name AS customer_name, c.email AS customer_email, "
                "       m.content AS body "
                "FROM tickets t "
                "JOIN customers c ON c.id = t.customer_id "
                "LEFT JOIN messages m ON m.conversation_id = t.conversation_id "
                "  AND m.role = 'customer' "
                "WHERE t.status = ANY($1::text[]) "
                "ORDER BY t.created_at ASC "
                "LIMIT $2",
                list(statuses),
                limit,
            )
            result: list[dict[str, Any]] = []
            seen: set[str] = set()
            for r in rows:
                internal_id = str(r["id"])
                if internal_id in seen:
                    continue
                seen.add(internal_id)
                result.append(
                    {
                        "ticket_id": "TKT-" + internal_id[:8].upper(),
                        "internal_id": internal_id,
                        "conversation_id": str(r["conversation_id"]) if r["conversation_id"] else None,
                        "customer_id": str(r["customer_id"]) if r["customer_id"] else None,
                        "status": r["status"],
                        "channel": r["channel"],
                        "subject": r["subject"],
                        "customer_name": r["customer_name"],
                        "customer_email": r["customer_email"],
                        "message": r["body"],
                    }
                )
            return result
    except Exception:
        logger.exception("get_pending_tickets failed")
        return []


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
    pgvector requires the embedding as a bracketed string: '[0.1,0.2,...]'
    """
    try:
        async with pool.acquire() as conn:
            # Short-circuit: skip vector search if KB is empty
            count = await conn.fetchval("SELECT COUNT(*) FROM knowledge_base")
            if not count:
                return []

            # pgvector requires a string literal, not a Python list
            embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

            rows = await conn.fetch(
                "SELECT id, title, content, category, "
                "       1 - (embedding <=> $1::vector) AS similarity "
                "FROM knowledge_base "
                "WHERE embedding IS NOT NULL "
                "ORDER BY embedding <=> $1::vector "
                "LIMIT $2",
                embedding_str,
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
                # Serialize embedding list to pgvector string format
                embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"

                if existing:
                    await conn.execute(
                        "UPDATE knowledge_base "
                        "SET content = $1, embedding = $2::vector, updated_at = NOW() "
                        "WHERE id = $3",
                        content,
                        embedding_str,
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
                    embedding_str,
                )
                return str(row["id"])
    except Exception:
        logger.exception("upsert_knowledge_base failed for title=%s", title)
        return None


# ---------------------------------------------------------------------------
# Metrics helper
# ---------------------------------------------------------------------------


async def get_sentiment_report(pool: asyncpg.Pool) -> dict[str, Any]:
    """Return today's sentiment report keyed to PKT midnight.

    Queries messages with non-NULL sentiment_score created today (PKT) and
    returns counts, averages, escalation rate, worst tickets, channel split,
    and a plain-language recommendation.
    """
    _PKT = ZoneInfo("Asia/Karachi")
    now = datetime.now(_PKT)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    _empty = {
        "date": now.strftime("%Y-%m-%d PKT"),
        "total_tickets_today": 0,
        "sentiment": {"positive": 0, "neutral": 0, "negative": 0, "avg_score": 0.0},
        "escalation_rate_today": "0%",
        "most_negative_tickets": [],
        "channel_breakdown": {ch: {"total": 0, "avg_sentiment": 0.0} for ch in ("web_form", "whatsapp", "email")},
        "recommendation": "No data available.",
    }

    try:
        async with pool.acquire() as conn:
            # Total tickets created today
            total_today = int(await conn.fetchval(
                "SELECT COUNT(*) FROM tickets WHERE created_at >= $1",
                today_start,
            ) or 0)

            # Escalated tickets today
            escalated_today = int(await conn.fetchval(
                "SELECT COUNT(*) FROM tickets WHERE created_at >= $1 AND status = 'escalated'",
                today_start,
            ) or 0)
            escalation_rate = round((escalated_today / total_today) * 100, 1) if total_today > 0 else 0.0

            # Sentiment breakdown from customer messages scored today
            sent_row = await conn.fetchrow(
                "SELECT "
                "  COUNT(*) FILTER (WHERE sentiment_score > 0.2)  AS positive, "
                "  COUNT(*) FILTER (WHERE sentiment_score >= -0.2 AND sentiment_score <= 0.2) AS neutral, "
                "  COUNT(*) FILTER (WHERE sentiment_score < -0.2) AS negative, "
                "  AVG(sentiment_score) AS avg_score "
                "FROM messages "
                "WHERE created_at >= $1 "
                "  AND role = 'customer' "
                "  AND sentiment_score IS NOT NULL",
                today_start,
            )
            positive  = int(sent_row["positive"]  or 0)
            neutral   = int(sent_row["neutral"]   or 0)
            negative  = int(sent_row["negative"]  or 0)
            avg_score = round(float(sent_row["avg_score"] or 0.0), 2)

            # Most negative tickets (by avg customer sentiment score, ascending)
            neg_rows = await conn.fetch(
                "SELECT t.id, t.subject, AVG(m.sentiment_score) AS avg_score "
                "FROM tickets t "
                "JOIN messages m ON m.conversation_id = t.conversation_id "
                "WHERE t.created_at >= $1 "
                "  AND m.role = 'customer' "
                "  AND m.sentiment_score IS NOT NULL "
                "GROUP BY t.id, t.subject "
                "ORDER BY avg_score ASC "
                "LIMIT 3",
                today_start,
            )
            most_negative = [
                {
                    "ticket_id": "TKT-" + str(r["id"])[:8].upper(),
                    "subject": r["subject"] or "(no subject)",
                    "score": round(float(r["avg_score"]), 2),
                }
                for r in neg_rows
            ]

            # Channel breakdown with average sentiment
            ch_rows = await conn.fetch(
                "SELECT t.channel, COUNT(DISTINCT t.id) AS total, AVG(m.sentiment_score) AS avg_sentiment "
                "FROM tickets t "
                "JOIN messages m ON m.conversation_id = t.conversation_id "
                "WHERE t.created_at >= $1 "
                "  AND m.role = 'customer' "
                "  AND m.sentiment_score IS NOT NULL "
                "GROUP BY t.channel",
                today_start,
            )
            channel_breakdown: dict[str, Any] = {
                r["channel"]: {
                    "total": int(r["total"]),
                    "avg_sentiment": round(float(r["avg_sentiment"] or 0.0), 2),
                }
                for r in ch_rows
            }
            for ch in ("web_form", "whatsapp", "email"):
                channel_breakdown.setdefault(ch, {"total": 0, "avg_sentiment": 0.0})

            # Recommendation text
            total_scored = positive + neutral + negative
            if total_scored == 0:
                recommendation = "No sentiment data for today yet."
            elif total_scored > 0 and (negative / total_scored) > 0.3:
                recommendation = "High negative sentiment detected. Review escalated tickets and consider proactive outreach."
            elif escalation_rate > 20:
                recommendation = "High escalation rate. Check agent workload and escalation thresholds."
            elif total_scored > 0 and (positive / total_scored) > 0.6:
                recommendation = "Low escalation rate. System performing well."
            else:
                recommendation = "Moderate sentiment. Monitor for emerging issues."

            return {
                "date": now.strftime("%Y-%m-%d PKT"),
                "total_tickets_today": total_today,
                "sentiment": {
                    "positive": positive,
                    "neutral": neutral,
                    "negative": negative,
                    "avg_score": avg_score,
                },
                "escalation_rate_today": f"{escalation_rate}%",
                "most_negative_tickets": most_negative,
                "channel_breakdown": channel_breakdown,
                "recommendation": recommendation,
            }
    except Exception:
        logger.exception("get_sentiment_report failed")
        return _empty


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


# ---------------------------------------------------------------------------
# User management helpers (Phase 7A — NextAuth RBAC)
# ---------------------------------------------------------------------------


async def get_user_by_email(pool: asyncpg.Pool, email: str) -> dict | None:
    """Return user row for the given email (case-insensitive), or None if not found."""
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, name, email, hashed_password, role "
                "FROM users WHERE email = $1",
                email.lower(),
            )
            return _serialize_row(row) if row else None
    except Exception:
        logger.exception("get_user_by_email failed for email=%s", email)
        return None


async def create_user(
    pool: asyncpg.Pool,
    name: str,
    email: str,
    hashed_password: str,
    role: str,
) -> dict:
    """Insert a new user and return id, name, email, role, created_at."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO users (name, email, hashed_password, role) "
            "VALUES ($1, $2, $3, $4) "
            "RETURNING id, name, email, role, created_at",
            name,
            email.lower(),
            hashed_password,
            role,
        )
        return _serialize_row(row)
