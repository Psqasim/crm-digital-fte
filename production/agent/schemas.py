"""
production/agent/schemas.py
Phase 4B: Pydantic v2 input models for the 5 parameterised function_tools.

These are the only schemas passed as single-argument inputs to @function_tool
functions that accept structured data (per ADR-0003).  Tools with simple
Annotated[str, ...] signatures do not need a schema here.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SearchKBInput(BaseModel):
    """Input for search_knowledge_base tool."""

    query: str = Field(
        description="Natural-language support query to search the knowledge base for.",
        min_length=1,
        max_length=500,
    )
    limit: int = Field(
        default=5,
        description="Maximum number of KB articles to return (1–20).",
        ge=1,
        le=20,
    )


class CreateTicketInput(BaseModel):
    """Input for create_ticket tool."""

    customer_id: str = Field(
        description="Customer UUID returned by get_or_create_customer."
    )
    conversation_id: str = Field(
        description="Conversation UUID for this interaction."
    )
    channel: str = Field(
        description="Support channel: 'email', 'whatsapp', or 'web_form'."
    )
    subject: str | None = Field(
        default=None,
        description="Short one-line ticket subject (optional).",
    )
    category: str | None = Field(
        default=None,
        description="Ticket category such as 'billing', 'technical', 'general' (optional).",
    )


class EscalateInput(BaseModel):
    """Input for escalate_to_human tool."""

    ticket_id: str = Field(
        description="UUID of the ticket to escalate."
    )
    reason: str = Field(
        description="Explanation of why this ticket requires human review.",
        min_length=1,
    )
    urgency: str = Field(
        default="medium",
        description="Escalation urgency level: 'low', 'medium', or 'high'.",
    )


class SendResponseInput(BaseModel):
    """Input for send_response tool."""

    ticket_id: str = Field(
        description="UUID from create_ticket — call create_ticket first to obtain this value."
    )
    message: str = Field(
        description="The response message body to send to the customer.",
        min_length=1,
    )
    channel: str = Field(
        description="Delivery channel: 'email', 'whatsapp', or 'web_form'."
    )
    thread_id: str | None = Field(
        default=None,
        description="Gmail threadId for email replies; required when channel=email.",
    )
    recipient: str | None = Field(
        default=None,
        description="Override recipient; uses ticket customer_email/phone if None.",
    )


class ResolveTicketInput(BaseModel):
    """Input for resolve_ticket tool."""

    ticket_id: str = Field(
        description="UUID of the ticket to mark as resolved."
    )
    resolution_summary: str = Field(
        description="Brief description of how the ticket was resolved.",
        min_length=1,
    )
