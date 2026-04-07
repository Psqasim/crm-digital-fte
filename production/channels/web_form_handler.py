"""
production/channels/web_form_handler.py
Phase 4C: Web form channel handler — HTTP form submission → DB → Kafka.

Flow:
  1. POST /support/submit → WebFormInput validated by FastAPI/Pydantic
  2. submit_ticket(): get/create customer → conversation → message → ticket → Kafka
  3. Returns TKT-XXXXXXXX display ID on success, None on any DB failure
  4. Kafka failure is best-effort: ticket is already in DB, do NOT raise
"""

from __future__ import annotations

import sys
from datetime import datetime
from typing import Literal
from uuid import uuid4
from zoneinfo import ZoneInfo

import asyncpg
from pydantic import BaseModel, EmailStr, Field

from production.channels.kafka_producer import publish_ticket
from production.database import queries
from src.agent.models import Channel, TicketMessage


# ---------------------------------------------------------------------------
# Pydantic v2 input model
# ---------------------------------------------------------------------------


class WebFormInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    subject: str = Field(min_length=5, max_length=200)
    category: Literal["billing", "technical", "account", "general"]
    priority: Literal["low", "medium", "high", "urgent"]
    message: str = Field(min_length=20, max_length=2000)


# ---------------------------------------------------------------------------
# Ticket submission pipeline
# ---------------------------------------------------------------------------


async def submit_ticket(
    pool: asyncpg.Pool,
    body: WebFormInput,
) -> dict | None:
    """Run the full ticket-creation pipeline and return the result dict, or None on error.

    Steps:
      A. get_or_create_customer
      B. create_conversation  (channel="web_form")
      C. add_message          (role="customer")
      D. create_ticket        (includes priority)
      E. publish_ticket to Kafka (best-effort — failure does NOT raise)
      F. return display ID dict

    On any exception in A-D: logs to stderr with [web_form_error] prefix and returns None.
    Kafka failures (step E) are logged but do NOT cause None return — ticket is already in DB.
    """
    try:
        # A — get or create customer
        customer = await queries.get_or_create_customer(pool, email=body.email, name=body.name)
        if customer is None:
            raise RuntimeError("get_or_create_customer returned None")

        customer_id = str(customer["id"])

        # B — create conversation
        conv_id = await queries.create_conversation(pool, customer_id=customer_id, channel="web_form")
        if conv_id is None:
            raise RuntimeError("create_conversation returned None")

        # C — add customer message
        _msg_id = await queries.add_message(
            pool,
            conversation_id=conv_id,
            role="customer",
            content=body.message,
            channel="web_form",
            sentiment_score=None,
        )

        # D — create ticket (with priority)
        ticket_id_uuid = await queries.create_ticket(
            pool,
            conversation_id=conv_id,
            customer_id=customer_id,
            channel="web_form",
            subject=body.subject,
            category=body.category,
            priority=body.priority,
        )
        if ticket_id_uuid is None:
            raise RuntimeError("create_ticket returned None")

        # E — publish to Kafka (best-effort: failure does not block response)
        current_dt = datetime.now(ZoneInfo("Asia/Karachi"))
        ticket_message = TicketMessage(
            id=str(uuid4()),
            channel=Channel.WEB_FORM,
            customer_name=body.name,
            customer_email=body.email,
            customer_phone=None,
            subject=body.subject,
            message=body.message,
            received_at=current_dt.isoformat(),
            metadata={},
        )
        try:
            await publish_ticket(ticket_message)
        except Exception as kafka_err:
            print(f"[kafka_error] web_form publish failed: {kafka_err}", file=sys.stderr)

        # F — return display ID
        display_id = "TKT-" + ticket_id_uuid[:8].upper()
        return {
            "ticket_id": display_id,
            "internal_id": ticket_id_uuid,
            "status": "open",
            "created_at": current_dt.isoformat(),
            "estimated_response_time": "~4 hours",
        }

    except Exception as e:
        print(f"[web_form_error] submit_ticket failed: {e}", file=sys.stderr)
        return None
