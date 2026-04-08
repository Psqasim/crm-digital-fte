"""
production/api/agent_routes.py
Phase 4D: Agent orchestration endpoints.

POST /agent/process/{ticket_id}  — process a single ticket through the AI agent
POST /agent/process-pending      — enqueue all open/pending tickets for processing
"""

from __future__ import annotations

import logging
from dataclasses import asdict

from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import JSONResponse

from production.agent.customer_success_agent import AgentResponse, CustomerContext, process_ticket
from production.database import queries
from production.database.queries import get_db_pool

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent")


# ---------------------------------------------------------------------------
# Background helper
# ---------------------------------------------------------------------------


async def _process_ticket_background(ticket_id: str) -> None:
    """Run process_ticket for a single ticket; called via BackgroundTasks."""
    try:
        pool = await get_db_pool()
        ticket = await queries.get_ticket_by_display_id(pool, ticket_id)
        if ticket is None:
            logger.warning("[agent_bg] ticket not found: %s", ticket_id)
            return
        await _run_agent_on_ticket(pool, ticket)
    except Exception:
        logger.exception("[agent_bg] failed processing ticket %s", ticket_id)


async def _run_agent_on_ticket(pool, ticket: dict) -> AgentResponse:
    """Core logic: build context, run agent, update DB, return AgentResponse."""
    ctx = CustomerContext(
        customer_id=ticket.get("customer_id") or "",
        customer_name=ticket.get("customer_name") or "Customer",
        customer_email=ticket.get("customer_email") or "",
        channel=ticket.get("channel") or "web",
        message=ticket.get("message") or ticket.get("subject") or "",
        conversation_id=ticket.get("conversation_id"),
    )

    agent_resp = await process_ticket(ctx)

    # Update ticket status in DB
    internal_id = ticket.get("internal_id") or ""
    if internal_id:
        new_status = "escalated" if agent_resp.escalated else "resolved"
        reason = (
            agent_resp.error
            if agent_resp.escalated
            else agent_resp.response_text[:200]
        )
        await queries.update_ticket_status(pool, internal_id, new_status, reason)

    # Persist agent response as a message
    conversation_id = ticket.get("conversation_id")
    channel = ctx.channel
    if conversation_id and agent_resp.response_text:
        await queries.add_message(
            pool,
            conversation_id,
            role="assistant",
            content=agent_resp.response_text,
            channel=channel,
        )

    return agent_resp


# ---------------------------------------------------------------------------
# POST /agent/process/{ticket_id}
# ---------------------------------------------------------------------------


@router.post("/process/{ticket_id}")
async def process_single_ticket(ticket_id: str) -> JSONResponse:
    """Load ticket from DB, run agent, update status, return AgentResponse JSON.

    Returns:
        200 with AgentResponse dict on success.
        404 if ticket not found.
        500 on unexpected error.
    """
    try:
        pool = await get_db_pool()
        ticket = await queries.get_ticket_by_display_id(pool, ticket_id)
        if ticket is None:
            return JSONResponse({"detail": f"Ticket {ticket_id} not found"}, status_code=404)

        agent_resp = await _run_agent_on_ticket(pool, ticket)
        return JSONResponse(_serialise_agent_response(agent_resp), status_code=200)

    except Exception:
        logger.exception("[agent] process_single_ticket failed for %s", ticket_id)
        return JSONResponse({"detail": "Internal server error"}, status_code=500)


# ---------------------------------------------------------------------------
# POST /agent/process-pending
# ---------------------------------------------------------------------------


@router.post("/process-pending")
async def process_pending_tickets(background_tasks: BackgroundTasks) -> JSONResponse:
    """Enqueue all open/pending tickets for background processing.

    Returns immediately with the count of tickets queued.
    Each ticket is processed asynchronously via BackgroundTasks.
    """
    try:
        pool = await get_db_pool()
        tickets = await queries.get_pending_tickets(pool)
        for t in tickets:
            background_tasks.add_task(_process_ticket_background, t["ticket_id"])
        return JSONResponse(
            {
                "queued": len(tickets),
                "ticket_ids": [t["ticket_id"] for t in tickets],
            },
            status_code=200,
        )
    except Exception:
        logger.exception("[agent] process_pending_tickets failed")
        return JSONResponse({"detail": "Internal server error"}, status_code=500)


# ---------------------------------------------------------------------------
# Serialisation helper
# ---------------------------------------------------------------------------


def _serialise_agent_response(resp: AgentResponse) -> dict:
    """Convert AgentResponse dataclass to a JSON-serialisable dict."""
    return {
        "ticket_id": resp.ticket_id,
        "response_text": resp.response_text,
        "channel": resp.channel,
        "escalated": resp.escalated,
        "escalation_id": resp.escalation_id,
        "resolution_status": resp.resolution_status,
        "error": resp.error,
    }
