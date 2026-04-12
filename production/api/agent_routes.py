"""
production/api/agent_routes.py
Phase 4D: Agent orchestration endpoints.

POST /agent/process/{ticket_id}  — process a single ticket through the AI agent
POST /agent/process-pending      — enqueue all open/pending tickets for processing
"""

from __future__ import annotations

import logging
import os
from dataclasses import asdict

from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from production.agent.customer_success_agent import AgentResponse, CustomerContext, process_ticket
from production.database import queries
from production.database.queries import get_db_pool

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent")


# ---------------------------------------------------------------------------
# Escalation notification helper
# ---------------------------------------------------------------------------


async def _notify_escalation(
    ticket_id: str,
    customer_name: str,
    subject: str,
    channel: str,
) -> None:
    """Send a WhatsApp alert to the admin when a ticket is escalated.

    Reads ADMIN_WHATSAPP_NUMBER from env (e.g. whatsapp:+923460326429).
    No-op if the env var is not set.
    """
    admin_phone = os.environ.get("ADMIN_WHATSAPP_NUMBER", "").strip()
    if not admin_phone:
        return
    try:
        from production.channels.whatsapp_handler import _get_handler as _get_wa_handler  # noqa: PLC0415
        handler = _get_wa_handler()
        message = (
            f"🚨 Escalated Ticket Alert\n"
            f"Ticket: {ticket_id}\n"
            f"Customer: {customer_name}\n"
            f"Subject: {subject or 'N/A'}\n"
            f"Channel: {channel}\n"
            f"Reply at: https://crm-digital-fte-two.vercel.app/ticket/{ticket_id}"
        )
        await handler.send_reply(admin_phone, message)
        logger.info("[escalation_notify] admin notified for ticket %s", ticket_id)
    except Exception:
        logger.exception("[escalation_notify] failed for ticket %s", ticket_id)


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
    display_ticket_id = ticket.get("ticket_id") or ""
    conversation_id_uuid = ticket.get("conversation_id") or ""
    customer_id_uuid = ticket.get("customer_id") or ""
    raw_message = ticket.get("message") or ticket.get("subject") or ""

    # Tell the agent the ticket already exists so it skips create_ticket.
    # Include real UUIDs so any tool calls use valid values.
    enriched_message = (
        f"[EXISTING TICKET — do NOT call create_ticket]\n"
        f"ticket_id={display_ticket_id} | conversation_id={conversation_id_uuid} | customer_id={customer_id_uuid}\n"
        f"Customer message: {raw_message}"
    ) if display_ticket_id else raw_message

    ctx = CustomerContext(
        customer_id=ticket.get("customer_id") or "",
        customer_name=ticket.get("customer_name") or "Customer",
        customer_email=ticket.get("customer_email") or "",
        channel=ticket.get("channel") or "web",
        message=enriched_message,
        conversation_id=ticket.get("conversation_id"),
    )

    agent_resp = await process_ticket(ctx)

    # If the agent didn't call create_ticket (ticket already exists), fill ticket_id from DB
    if agent_resp.ticket_id is None and display_ticket_id:
        agent_resp.ticket_id = display_ticket_id

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

        # Notify admin on WhatsApp when ticket is escalated
        if agent_resp.escalated:
            await _notify_escalation(
                ticket_id=display_ticket_id,
                customer_name=ticket.get("customer_name") or "Customer",
                subject=ticket.get("subject") or raw_message[:80],
                channel=ctx.channel,
            )

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
# POST /agent/reply — human agent sends a reply to an escalated ticket
# ---------------------------------------------------------------------------


class AgentReplyBody(BaseModel):
    ticket_id: str
    message: str
    agent_email: str


@router.post("/reply")
async def agent_reply(body: AgentReplyBody) -> JSONResponse:
    """Allow a human agent to reply to a ticket.

    Adds a message with role='agent' to the ticket's conversation.
    Changes ticket status from 'escalated' → 'in_progress'.

    Returns:
        200 with {success: true, message_id: str}
        400 if message is empty
        404 if ticket not found
        500 on DB error
    """
    if not body.message.strip():
        return JSONResponse({"detail": "Message cannot be empty"}, status_code=400)

    try:
        pool = await get_db_pool()
        ticket = await queries.get_ticket_by_display_id(pool, body.ticket_id)
        if ticket is None:
            return JSONResponse(
                {"detail": f"Ticket {body.ticket_id} not found"}, status_code=404
            )

        conversation_id = ticket.get("conversation_id")
        internal_id = ticket.get("internal_id")

        if not conversation_id:
            return JSONResponse(
                {"detail": "Ticket has no conversation"}, status_code=400
            )

        # Add human agent reply as role='agent'
        message_id = await queries.add_message(
            pool,
            conversation_id,
            role="agent",
            content=body.message.strip(),
            channel="web_form",
        )

        # Move ticket from escalated → in_progress (being handled)
        if internal_id and ticket.get("status") == "escalated":
            await queries.update_ticket_status(pool, internal_id, "in_progress")

        # Send reply back via original channel
        ticket_channel = ticket.get("channel", "")
        if ticket_channel == "whatsapp":
            # customer_name is the phone number for WhatsApp tickets
            customer_phone = (ticket.get("customer_name") or "").strip()
            if customer_phone.startswith("+"):
                try:
                    from production.channels.whatsapp_handler import _get_handler as _get_wa_handler  # noqa: PLC0415
                    wa_handler = _get_wa_handler()
                    await wa_handler.send_reply(customer_phone, body.message.strip())
                    logger.info(
                        "[agent_reply] WhatsApp reply sent to %s for ticket %s",
                        customer_phone,
                        body.ticket_id,
                    )
                except Exception:
                    logger.exception(
                        "[agent_reply] failed to send WhatsApp reply for ticket %s",
                        body.ticket_id,
                    )
                    # Message already saved to DB — don't fail the request

        logger.info(
            "[agent_reply] %s replied to ticket %s (msg_id=%s)",
            body.agent_email,
            body.ticket_id,
            message_id,
        )
        return JSONResponse(
            {"success": True, "message_id": message_id or ""},
            status_code=200,
        )

    except Exception:
        logger.exception("[agent_reply] failed for ticket %s", body.ticket_id)
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
