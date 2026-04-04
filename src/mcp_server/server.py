"""
server.py — FastMCP stdio server for NexaFlow CRM Tool Gateway.

Phase 2D: Exposes 7 tools wrapping Phase 2B/2C agent modules.

IMPORTANT: No print() statements. All logging goes to stderr only.
Writing to stdout would corrupt JSON-RPC messages.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP

from src.agent.conversation_store import (
    Message,
    get_store,
    reset_store,
)
from src.agent.knowledge_base import KnowledgeBase
from src.agent.models import Channel, TicketStatus

# ---------------------------------------------------------------------------
# Logging — stderr ONLY (stdout is reserved for JSON-RPC)
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("nexaflow.mcp")

# ---------------------------------------------------------------------------
# Module-level singletons
# ---------------------------------------------------------------------------

_kb = KnowledgeBase()
store = get_store()

# Ticket index: ticket_id → conversation_id
# Populated by create_ticket; used by escalate_to_human, send_response, resolve_ticket.
# NOTE: Process-local only — cleared on server restart (acceptable in Phase 2D in-memory scope).
_ticket_index: dict[str, str] = {}

# ---------------------------------------------------------------------------
# FastMCP server
# ---------------------------------------------------------------------------

mcp = FastMCP("nexaflow-crm")

# ---------------------------------------------------------------------------
# Tool 1 — search_knowledge_base
# ---------------------------------------------------------------------------


@mcp.tool()
async def search_knowledge_base(query: str) -> str:
    """Search NexaFlow product documentation for relevant information.

    Args:
        query: The search query. Use natural language describing the customer's issue.
    """
    if not query or not query.strip():
        return json.dumps({
            "error": "validation: query must not be empty",
            "tool": "search_knowledge_base",
        })
    try:
        results = _kb.search(query.strip(), top_k=3)
        return json.dumps({
            "results": [
                {
                    "section_title": r.section_title,
                    "content": r.content,
                    "relevance_score": r.relevance_score,
                }
                for r in results
            ],
            "count": len(results),
            "query": query,
        })
    except Exception as e:
        logger.error("search_knowledge_base error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "tool": "search_knowledge_base"})


# ---------------------------------------------------------------------------
# Tool 2 — create_ticket
# ---------------------------------------------------------------------------

_VALID_PRIORITIES = {"low", "medium", "high", "critical"}
_VALID_CHANNELS = {"email", "whatsapp", "web_form"}


@mcp.tool()
async def create_ticket(
    customer_id: str,
    issue: str,
    priority: str,
    channel: str,
) -> str:
    """Create a new support ticket for a customer.

    Args:
        customer_id: Customer email address (primary key) or phone:+1234567890 for WhatsApp.
        issue: Description of the customer's issue (used as conversation topic).
        priority: Ticket priority. One of: low, medium, high, critical.
        channel: Originating channel. One of: email, whatsapp, web_form.
    """
    if not customer_id or not customer_id.strip():
        return json.dumps({
            "error": "validation: customer_id must not be empty",
            "tool": "create_ticket",
        })
    if not issue or not issue.strip():
        return json.dumps({
            "error": "validation: issue must not be empty",
            "tool": "create_ticket",
        })
    if priority not in _VALID_PRIORITIES:
        return json.dumps({
            "error": "validation: priority must be one of: low, medium, high, critical",
            "tool": "create_ticket",
        })
    if channel not in _VALID_CHANNELS:
        return json.dumps({
            "error": "validation: channel must be one of: email, whatsapp, web_form",
            "tool": "create_ticket",
        })
    try:
        store.get_or_create_customer(key=customer_id, name=customer_id, channel=channel)
        conv = store.get_or_create_conversation(customer_key=customer_id, channel=channel)
        store.add_topic(conv.id, issue[:100])
        ticket_id = conv.ticket.id
        # Populate ticket index — critical for all ticket-scoped tools
        _ticket_index[ticket_id] = conv.id
        return json.dumps({
            "ticket_id": ticket_id,
            "customer_id": customer_id,
            "status": "open",
            "channel": channel,
            "created_at": conv.ticket.opened_at,
        })
    except Exception as e:
        logger.error("create_ticket error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "tool": "create_ticket"})


# ---------------------------------------------------------------------------
# Tool 3 — get_customer_history
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_customer_history(customer_id: str) -> str:
    """Retrieve full interaction history for a customer across all channels.

    Args:
        customer_id: Customer email address or phone:+1234567890.
    """
    if not customer_id or not customer_id.strip():
        return json.dumps({
            "error": "validation: customer_id must not be empty",
            "tool": "get_customer_history",
        })
    try:
        profile = store.get_customer(customer_id)
        if profile is None:
            return json.dumps({
                "customer_id": customer_id,
                "name": None,
                "channels_used": [],
                "conversation_count": 0,
                "conversations": [],
            })
        conversations = []
        for conv_id in profile.conversation_ids:
            # Access internal dict — documented: Phase 4 will use DB queries
            conv = store._conversations.get(conv_id)
            if conv is not None:
                conversations.append({
                    "conversation_id": conv.id,
                    "channel": conv.channel_origin,
                    "ticket_id": conv.ticket.id,
                    "ticket_status": conv.ticket.status.value,
                    "message_count": len(conv.messages),
                    "created_at": conv.created_at,
                })
        return json.dumps({
            "customer_id": customer_id,
            "name": profile.name,
            "channels_used": list(profile.channels_used),
            "conversation_count": len(conversations),
            "conversations": conversations,
        })
    except Exception as e:
        logger.error("get_customer_history error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "tool": "get_customer_history"})


# ---------------------------------------------------------------------------
# Tool 4 — escalate_to_human
# ---------------------------------------------------------------------------


@mcp.tool()
async def escalate_to_human(ticket_id: str, reason: str) -> str:
    """Escalate a support ticket to a human agent.

    Args:
        ticket_id: The ticket identifier returned by create_ticket (e.g. TKT-a1b2c3d4).
        reason: Human-readable reason for escalation (e.g. "customer requested human agent").
    """
    if not ticket_id or not ticket_id.strip():
        return json.dumps({
            "error": "validation: ticket_id must not be empty",
            "tool": "escalate_to_human",
        })
    if not reason or not reason.strip():
        return json.dumps({
            "error": "validation: reason must not be empty",
            "tool": "escalate_to_human",
        })
    try:
        conv_id = _ticket_index.get(ticket_id)
        if conv_id is None:
            return json.dumps({
                "error": f"ticket {ticket_id} not found",
                "tool": "escalate_to_human",
            })
        try:
            store.transition_ticket(conv_id, TicketStatus.ESCALATED)
        except ValueError as ve:
            return json.dumps({"error": str(ve), "tool": "escalate_to_human"})

        escalation_id = "ESC-" + uuid.uuid4().hex[:8]

        # Optional LLM enrichment — skip gracefully when key absent
        if not os.getenv("OPENAI_API_KEY"):
            logger.warning(
                "OPENAI_API_KEY absent — escalating unconditionally without AI eval"
            )

        return json.dumps({
            "escalation_id": escalation_id,
            "ticket_id": ticket_id,
            "status": "escalated",
            "reason": reason,
            "escalated_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        logger.error("escalate_to_human error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "tool": "escalate_to_human"})


# ---------------------------------------------------------------------------
# Tool 5 — send_response
# ---------------------------------------------------------------------------


@mcp.tool()
async def send_response(ticket_id: str, message: str, channel: str) -> str:
    """Send a response message to a customer through a specific channel.

    Delivery is simulated (logged to stderr) in Phase 2D.
    Real channel dispatch (Gmail, Twilio) is deferred to Phase 4.

    Args:
        ticket_id: The ticket identifier returned by create_ticket.
        message: The response message body to send to the customer.
        channel: Delivery channel. One of: email, whatsapp, web_form.
    """
    if channel not in _VALID_CHANNELS:
        return json.dumps({
            "error": "validation: channel must be one of: email, whatsapp, web_form",
            "tool": "send_response",
        })
    if not message or not message.strip():
        return json.dumps({
            "error": "validation: message must not be empty",
            "tool": "send_response",
        })
    try:
        conv_id = _ticket_index.get(ticket_id)
        if conv_id is None:
            return json.dumps({
                "error": f"ticket {ticket_id} not found",
                "tool": "send_response",
            })
        now = datetime.now(timezone.utc).isoformat()
        msg = Message(
            id=f"msg-{uuid.uuid4().hex[:8]}",
            text=message,
            channel=channel,
            direction="outbound",
            timestamp=now,
            sentiment_score=None,
        )
        store.add_message(conv_id, msg)
        # Log delivery simulation to stderr only — never stdout
        logger.info(
            "[SIMULATED SEND] channel=%s ticket=%s len=%d",
            channel, ticket_id, len(message),
        )
        return json.dumps({
            "delivery_status": "delivered",
            "ticket_id": ticket_id,
            "channel": channel,
            "message_length": len(message),
            "timestamp": now,
        })
    except Exception as e:
        logger.error("send_response error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "tool": "send_response"})


# ---------------------------------------------------------------------------
# Tool 6 — get_sentiment_trend
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_sentiment_trend(customer_id: str) -> str:
    """Analyse sentiment trend for a customer based on recent interactions.

    Returns a trend label (improving/stable/deteriorating) and escalation recommendation.

    Args:
        customer_id: Customer email address or phone:+1234567890.
    """
    if not customer_id or not customer_id.strip():
        return json.dumps({
            "error": "validation: customer_id must not be empty",
            "tool": "get_sentiment_trend",
        })
    try:
        profile = store.get_customer(customer_id)
        if profile is None:
            return json.dumps({
                "customer_id": customer_id,
                "trend": "stable",
                "window_scores": [],
                "window_size": 3,
                "recommend_escalation": False,
                "note": "no history found",
            })
        # Get active or most recent conversation
        conv = store.get_active_conversation(customer_id)
        if conv is None and profile.conversation_ids:
            conv = store._conversations.get(profile.conversation_ids[-1])
        if conv is None:
            return json.dumps({
                "customer_id": customer_id,
                "trend": "stable",
                "window_scores": [],
                "window_size": 3,
                "recommend_escalation": False,
                "note": "no conversation found",
            })
        trend = store.compute_sentiment_trend(conv)
        result: dict = {
            "customer_id": customer_id,
            "trend": trend.label.value,
            "window_scores": trend.window_scores,
            "window_size": trend.window_size,
            "recommend_escalation": trend.label.value == "deteriorating",
        }
        if len(trend.window_scores) < 2:
            result["note"] = "insufficient data"
        return json.dumps(result)
    except Exception as e:
        logger.error("get_sentiment_trend error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "tool": "get_sentiment_trend"})


# ---------------------------------------------------------------------------
# Tool 7 — resolve_ticket
# ---------------------------------------------------------------------------


@mcp.tool()
async def resolve_ticket(ticket_id: str, resolution_summary: str) -> str:
    """Mark a support ticket as resolved with a resolution summary.

    Args:
        ticket_id: The ticket identifier returned by create_ticket.
        resolution_summary: A brief description of how the issue was resolved.
    """
    if not resolution_summary or not resolution_summary.strip():
        return json.dumps({
            "error": "validation: resolution_summary must not be empty",
            "tool": "resolve_ticket",
        })
    if not ticket_id or not ticket_id.strip():
        return json.dumps({
            "error": "validation: ticket_id must not be empty",
            "tool": "resolve_ticket",
        })
    try:
        conv_id = _ticket_index.get(ticket_id)
        if conv_id is None:
            return json.dumps({
                "error": f"ticket {ticket_id} not found",
                "tool": "resolve_ticket",
            })
        # Access internal dict — Phase 4 will replace with DB query
        conv = store._conversations[conv_id]
        # Idempotency: already resolved → return existing resolution without state change
        if conv.ticket.status == TicketStatus.RESOLVED:
            return json.dumps({
                "ticket_id": ticket_id,
                "status": "resolved",
                "note": "ticket was already resolved",
                "resolved_at": conv.ticket.closed_at,
            })
        # ESCALATED is a terminal state — cannot resolve directly
        if conv.ticket.status == TicketStatus.ESCALATED:
            return json.dumps({
                "error": "Cannot resolve escalated ticket directly",
                "tool": "resolve_ticket",
            })
        try:
            # Auto-cascade: OPEN → PENDING → RESOLVED (agent may skip send_response step)
            if conv.ticket.status == TicketStatus.OPEN:
                store.transition_ticket(conv_id, TicketStatus.PENDING)
            store.transition_ticket(conv_id, TicketStatus.RESOLVED)
        except ValueError as ve:
            return json.dumps({"error": str(ve), "tool": "resolve_ticket"})

        store.add_topic(conv_id, f"resolved:{resolution_summary[:100]}")
        return json.dumps({
            "ticket_id": ticket_id,
            "status": "resolved",
            "resolution_summary": resolution_summary,
            "resolved_at": conv.ticket.closed_at,
        })
    except Exception as e:
        logger.error("resolve_ticket error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "tool": "resolve_ticket"})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
