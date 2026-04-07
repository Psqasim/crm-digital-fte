"""
production/agent/tools.py
Phase 4B: 7 @function_tool functions for the NexaFlow Customer Success agent.

Design decisions:
- Each tool has a _*_impl() async function containing the logic, and a thin
  @function_tool wrapper that calls it.  This separation makes unit testing
  trivial (call _impl directly without invoking the FunctionTool wrapper).
- All tools return JSON strings (str) — never raise naked exceptions.
- Errors return {"error": str(e), "tool": "<name>"} and log to stderr.
- OpenAI AsyncOpenAI client is a lazy singleton (_get_openai_client).
- asyncpg pool is retrieved via get_db_pool() (ADR-0001 injectable pool pattern).
- Module-level _ticket_registry tracks ticket states for idempotency guards.
"""

from __future__ import annotations

import json
import statistics
import sys
import uuid
from datetime import datetime, timezone
from typing import Annotated
from zoneinfo import ZoneInfo

from agents import function_tool
from openai import AsyncOpenAI
from pydantic import Field

from production.agent.formatters import (
    format_email_response,
    format_web_form_response,
    format_whatsapp_response,
)
from production.agent.schemas import (
    CreateTicketInput,
    EscalateInput,
    ResolveTicketInput,
    SearchKBInput,
    SendResponseInput,
)
from production.database import queries
from production.database.queries import get_db_pool

# ---------------------------------------------------------------------------
# OpenAI client singleton
# ---------------------------------------------------------------------------

_openai_client: AsyncOpenAI | None = None

# Ticket state registry — tracks status of tickets created in this process.
# Keys: ticket_id (str UUID); Values: "open" | "escalated" | "resolved"
_ticket_registry: dict[str, str] = {}

# Customer name lookup for formatters (populated externally by process_ticket)
_CUSTOMER_NAMES: dict[str, str] = {}
_DEFAULT_CUSTOMER_NAME = "Valued Customer"


def _get_openai_client() -> AsyncOpenAI:
    """Lazy singleton: initialises AsyncOpenAI from OPENAI_API_KEY env var."""
    global _openai_client
    if _openai_client is None:
        import os
        _openai_client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
    return _openai_client


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


# ---------------------------------------------------------------------------
# Tool 1: search_knowledge_base
# ---------------------------------------------------------------------------


async def _search_knowledge_base_impl(params: SearchKBInput) -> str:
    try:
        client = _get_openai_client()
        resp = await client.embeddings.create(
            model="text-embedding-3-small",
            input=params.query,
        )
        embedding: list[float] = resp.data[0].embedding

        pool = await get_db_pool()
        results = await queries.search_knowledge_base(pool, embedding, params.limit)

        return json.dumps({
            "results": [
                {
                    "id": str(r.get("id", "")),
                    "title": r.get("title", ""),
                    "content": r.get("content", ""),
                    "category": r.get("category", ""),
                    "similarity": float(r.get("similarity", 0.0)),
                }
                for r in results
            ],
            "count": len(results),
        })
    except Exception as e:
        print(f"[search_knowledge_base ERROR] {e}", file=sys.stderr)
        return json.dumps({"error": str(e), "tool": "search_knowledge_base"})


@function_tool
async def search_knowledge_base(params: SearchKBInput) -> str:
    """Search NexaFlow's knowledge base for articles relevant to the customer's question.

    Generates a vector embedding of the query and performs cosine similarity search.
    Returns the most relevant articles with similarity scores.

    Use this AFTER create_ticket and get_customer_history to find product answers.
    """
    return await _search_knowledge_base_impl(params)


# ---------------------------------------------------------------------------
# Tool 2: create_ticket
# ---------------------------------------------------------------------------


async def _create_ticket_impl(params: CreateTicketInput) -> str:
    try:
        pool = await get_db_pool()
        ticket_id = await queries.create_ticket(
            pool,
            params.conversation_id,
            params.customer_id,
            params.channel,
            params.subject,
            params.category,
        )
        if ticket_id is None:
            raise RuntimeError("create_ticket query returned None — check DB logs")

        _ticket_registry[ticket_id] = "open"

        return json.dumps({
            "ticket_id": ticket_id,
            "customer_id": params.customer_id,
            "conversation_id": params.conversation_id,
            "channel": params.channel,
            "status": "open",
            "created_at": _utc_now(),
        })
    except Exception as e:
        print(f"[create_ticket ERROR] {e}", file=sys.stderr)
        return json.dumps({"error": str(e), "tool": "create_ticket"})


@function_tool
async def create_ticket(params: CreateTicketInput) -> str:
    """Register this customer interaction as a support ticket.

    MUST be called first — before get_customer_history, search_knowledge_base,
    or send_response. Returns a ticket_id required by send_response and resolve_ticket.
    """
    return await _create_ticket_impl(params)


# ---------------------------------------------------------------------------
# Tool 3: get_customer_history
# ---------------------------------------------------------------------------


async def _get_customer_history_impl(customer_id: str, limit: int = 20) -> str:
    try:
        pool = await get_db_pool()
        conversations = await queries.get_customer_history(pool, customer_id, limit)

        serialised = []
        for conv in conversations:
            c = dict(conv)
            for key in ("started_at", "updated_at"):
                if hasattr(c.get(key), "isoformat"):
                    c[key] = c[key].isoformat()
            msgs = []
            for msg in c.get("messages", []):
                m = dict(msg)
                if hasattr(m.get("created_at"), "isoformat"):
                    m["created_at"] = m["created_at"].isoformat()
                msgs.append(m)
            c["messages"] = msgs
            serialised.append(c)

        return json.dumps({
            "conversations": serialised,
            "count": len(serialised),
        })
    except Exception as e:
        print(f"[get_customer_history ERROR] {e}", file=sys.stderr)
        return json.dumps({"error": str(e), "tool": "get_customer_history"})


@function_tool
async def get_customer_history(
    customer_id: Annotated[str, Field(description="Customer UUID from create_ticket or CRM lookup.")],
    limit: int = 20,
) -> str:
    """Retrieve all prior support interactions for this customer across all channels.

    ALWAYS call this on every interaction to check for prior contact history.
    If prior conversations exist, acknowledge them in the response (ALWAYS-3 rule).
    """
    return await _get_customer_history_impl(customer_id, limit)


# ---------------------------------------------------------------------------
# Tool 4: escalate_to_human
# ---------------------------------------------------------------------------


async def _escalate_to_human_impl(params: EscalateInput) -> str:
    try:
        escalation_id = str(uuid.uuid4())
        pool = await get_db_pool()
        await queries.update_ticket_status(
            pool, params.ticket_id, status="escalated", reason=params.reason
        )
        _ticket_registry[params.ticket_id] = "escalated"

        return json.dumps({
            "escalation_id": escalation_id,
            "ticket_id": params.ticket_id,
            "status": "escalated",
            "reason": params.reason,
            "urgency": params.urgency,
            "escalated_at": _utc_now(),
        })
    except Exception as e:
        print(f"[escalate_to_human ERROR] {e}", file=sys.stderr)
        return json.dumps({"error": str(e), "tool": "escalate_to_human"})


@function_tool
async def escalate_to_human(params: EscalateInput) -> str:
    """Escalate this ticket to a human support agent.

    Use when: customer explicitly requests human, sentiment < 0.3, 3+ unresolved tickets,
    billing dispute, legal/compliance issue, data loss, or API/security incident.

    Returns an escalation_id. Idempotent — re-escalating an already-escalated ticket
    generates a new escalation_id but does not error.
    """
    return await _escalate_to_human_impl(params)


# ---------------------------------------------------------------------------
# Tool 5: send_response
# ---------------------------------------------------------------------------


async def _send_response_impl(params: SendResponseInput) -> str:
    # Lazy imports inside function body to prevent circular imports
    # (tools.py → gmail_handler.py → kafka_producer.py → models.py)
    from production.channels.gmail_handler import GmailHandler
    from production.channels.whatsapp_handler import WhatsAppHandler

    try:
        customer_name = _CUSTOMER_NAMES.get(params.ticket_id, _DEFAULT_CUSTOMER_NAME)

        if params.channel == "email":
            formatted = format_email_response(params.message, customer_name)
        elif params.channel == "whatsapp":
            formatted = format_whatsapp_response(params.message, customer_name)
        elif params.channel == "web_form":
            formatted = format_web_form_response(params.message, customer_name)
        else:
            from production.agent.formatters import FormattedResponse
            formatted = FormattedResponse(
                formatted_text=params.message,
                channel=params.channel,
                formatting_notes=["unknown_channel_passthrough"],
            )

        try:
            if params.channel == "email":
                handler = GmailHandler()
                await handler.setup_credentials()
                thread_id = params.thread_id or ""
                recipient = params.recipient or ""
                await handler.send_reply(
                    thread_id=thread_id,
                    to_email=recipient,
                    body=formatted.formatted_text,
                )
            elif params.channel == "whatsapp":
                handler = WhatsAppHandler()
                recipient = params.recipient or ""
                await handler.send_reply(
                    to_phone=recipient,
                    body=formatted.formatted_text,
                )
            elif params.channel == "web_form":
                # Phase 4C-iii: FastAPI handles web_form outbound
                pass
        except Exception as dispatch_err:
            print(f"[send_response dispatch ERROR] {dispatch_err}", file=sys.stderr)
            return json.dumps({
                "delivery_status": "failed",
                "error": str(dispatch_err),
                "channel": params.channel,
            })

        return json.dumps({
            "delivery_status": "delivered",
            "channel": params.channel,
            "timestamp": datetime.now(ZoneInfo("Asia/Karachi")).isoformat(),
        })
    except Exception as e:
        print(f"[send_response ERROR] {e}", file=sys.stderr)
        return json.dumps({
            "delivery_status": "failed",
            "error": str(e),
            "channel": params.channel,
        })


@function_tool
async def send_response(params: SendResponseInput) -> str:
    """Send a formatted response to the customer via their channel.

    STUB — real channel dispatch is wired in Phase 4C.
    Applies channel-specific formatting (greeting, limits, signature) before delivery.
    Logs the formatted message to stderr for Phase 4C pickup.

    MUST be called AFTER create_ticket — ticket_id is required.
    """
    return await _send_response_impl(params)


# ---------------------------------------------------------------------------
# Tool 6: get_sentiment_trend
# ---------------------------------------------------------------------------


async def _get_sentiment_trend_impl(customer_id: str, last_n: int = 5) -> str:
    try:
        pool = await get_db_pool()
        scores: list[float] = await queries.get_sentiment_trend(pool, customer_id, last_n)

        if not scores:
            return json.dumps({
                "scores": [],
                "count": 0,
                "trend": "insufficient_data",
                "recommend_escalation": False,
            })

        if len(scores) < 2:
            trend = "insufficient_data"
        elif scores[-1] > scores[0] + 0.2:
            trend = "improving"
        elif scores[-1] < scores[0] - 0.2:
            trend = "deteriorating"
        else:
            trend = "stable"

        avg = statistics.mean(scores)
        recommend_escalation = avg < 0.3

        return json.dumps({
            "scores": scores,
            "count": len(scores),
            "trend": trend,
            "recommend_escalation": recommend_escalation,
        })
    except Exception as e:
        print(f"[get_sentiment_trend ERROR] {e}", file=sys.stderr)
        return json.dumps({"error": str(e), "tool": "get_sentiment_trend"})


@function_tool
async def get_sentiment_trend(
    customer_id: Annotated[str, Field(description="Customer UUID to retrieve sentiment history for.")],
    last_n: int = 5,
) -> str:
    """Retrieve sentiment score trend for this customer over their last N messages.

    ALWAYS call before resolve_ticket when sentiment trend is unknown.
    If average score < 0.3, recommend_escalation = True and escalate before closing.

    Trend labels:
    - improving: last score > first score + 0.2
    - deteriorating: last score < first score - 0.2
    - stable: otherwise (including insufficient data)
    """
    return await _get_sentiment_trend_impl(customer_id, last_n)


# ---------------------------------------------------------------------------
# Tool 7: resolve_ticket
# ---------------------------------------------------------------------------


async def _resolve_ticket_impl(params: ResolveTicketInput) -> str:
    try:
        current_status = _ticket_registry.get(params.ticket_id)

        if current_status == "escalated":
            return json.dumps({
                "error": "cannot resolve escalated ticket — ticket is awaiting human review",
                "tool": "resolve_ticket",
                "ticket_id": params.ticket_id,
            })

        if current_status == "resolved":
            return json.dumps({
                "ticket_id": params.ticket_id,
                "status": "resolved",
                "resolution_summary": params.resolution_summary,
                "resolved_at": _utc_now(),
                "note": "ticket was already resolved",
            })

        pool = await get_db_pool()
        await queries.update_ticket_status(
            pool, params.ticket_id, status="resolved", reason=params.resolution_summary
        )
        _ticket_registry[params.ticket_id] = "resolved"

        return json.dumps({
            "ticket_id": params.ticket_id,
            "status": "resolved",
            "resolution_summary": params.resolution_summary,
            "resolved_at": _utc_now(),
        })
    except Exception as e:
        print(f"[resolve_ticket ERROR] {e}", file=sys.stderr)
        return json.dumps({"error": str(e), "tool": "resolve_ticket"})


@function_tool
async def resolve_ticket(params: ResolveTicketInput) -> str:
    """Mark a support ticket as resolved with a resolution summary.

    Idempotent: calling on an already-resolved ticket returns the existing record.
    Cannot resolve an escalated ticket — returns an error (use escalate_to_human instead).
    Call get_sentiment_trend before resolving; escalate if avg sentiment < 0.3.
    """
    return await _resolve_ticket_impl(params)
