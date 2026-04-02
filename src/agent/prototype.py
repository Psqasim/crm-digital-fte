from __future__ import annotations

import re
import os
import time
import uuid
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

from openai import OpenAI

from src.agent.channel_formatter import format_response
from src.agent.conversation_store import (
    URGENCY_SCORE_MAP,
    Message,
    get_store,
)
from src.agent.escalation_evaluator import evaluate_escalation
from src.agent.knowledge_base import KnowledgeBase
from src.agent.models import (
    AgentResponse,
    Channel,
    EscalationDecision,
    KBResult,
    NormalizedTicket,
    TicketMessage,
    TicketStatus,
)
from src.agent.prompts import get_system_prompt

_kb = KnowledgeBase()
_openai_client: OpenAI | None = None

_ESCALATION_ACK_TEMPLATE = (
    "Thank you for reaching out. We understand this is urgent and want to make sure "
    "you get the right support. Your case has been escalated to our team and a human "
    "agent will be in touch with you shortly. We apologize for any inconvenience."
)


def _get_openai() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    return _openai_client


def _make_inbound_message(ticket: NormalizedTicket, escalation: EscalationDecision, dt_str: str) -> Message:
    """Create an inbound Message with sentiment_score derived from escalation decision."""
    if escalation.should_escalate:
        score_key = (escalation.urgency, True)
    else:
        score_key = (None, False)
    sentiment_score = URGENCY_SCORE_MAP.get(score_key, 0.80)
    return Message(
        id=f"msg-{uuid.uuid4().hex[:8]}",
        text=ticket.message,
        channel=ticket.channel.value,
        direction="inbound",
        timestamp=dt_str,
        sentiment_score=sentiment_score,
    )


def _make_outbound_message(text: str, channel: Channel, dt_str: str) -> Message:
    return Message(
        id=f"msg-{uuid.uuid4().hex[:8]}",
        text=text,
        channel=channel.value,
        direction="outbound",
        timestamp=dt_str,
        sentiment_score=None,
    )


# ---------------------------------------------------------------------------
# T004 — normalize_message
# ---------------------------------------------------------------------------

def normalize_message(msg: TicketMessage) -> NormalizedTicket:
    """Convert a raw TicketMessage into a channel-agnostic NormalizedTicket."""
    first_name = msg.customer_name.split()[0] if msg.customer_name else msg.customer_name

    has_email = bool(msg.customer_email)
    has_phone = bool(msg.customer_phone)
    if has_email and has_phone:
        identifier_type = "both"
    elif has_email:
        identifier_type = "email"
    else:
        identifier_type = "phone"

    if msg.channel == Channel.EMAIL:
        inferred_topic = msg.subject or " ".join(msg.message.split()[:10])
    elif msg.channel == Channel.WHATSAPP:
        inferred_topic = " ".join(msg.message.split()[:10])
    else:  # web_form
        inferred_topic = msg.subject or " ".join(msg.message.split()[:10])

    word_count = len(msg.message.split())

    non_ascii = sum(1 for c in msg.message if ord(c) > 127)
    if non_ascii / max(len(msg.message), 1) > 0.15:
        language_hint = "non_en"
    elif msg.message.lower().split()[:1] and msg.message.lower().split()[0] in ("hola", "ayuda", "estoy"):
        language_hint = "es"
    else:
        language_hint = "en"

    category_hint = msg.category if msg.channel == Channel.WEB_FORM else None

    return NormalizedTicket(
        ticket_id=msg.id,
        channel=msg.channel,
        customer_name=msg.customer_name,
        customer_first_name=first_name,
        customer_email=msg.customer_email,
        customer_phone=msg.customer_phone,
        identifier_type=identifier_type,
        inferred_topic=inferred_topic,
        message=msg.message,
        message_word_count=word_count,
        category_hint=category_hint,
        received_at=msg.received_at,
        source_metadata=msg.metadata,
        language_hint=language_hint,
    )


# ---------------------------------------------------------------------------
# T010 — process_ticket (core loop)
# ---------------------------------------------------------------------------

def process_ticket(msg: TicketMessage) -> AgentResponse:
    """Full 6-step core loop: normalize → KB search → escalation check →
    (escalate OR generate+format) → return AgentResponse.
    """
    start_ms = time.monotonic() * 1000

    # Step 1: Normalize
    ticket = normalize_message(msg)

    # Step 1b: Resolve identity + load history (T015)
    store = get_store()
    customer_key = store.resolve_identity(
        email=ticket.customer_email,
        phone=ticket.customer_phone,
    )

    # T022: If customer_key is transient phone: key, try to extract email from message text
    if customer_key.startswith("phone:") and ticket.customer_phone:
        extracted_emails = re.findall(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}", ticket.message)
        if extracted_emails:
            extracted_email = extracted_emails[0]
            store.link_phone_to_email(ticket.customer_phone, extracted_email)
            customer_key = store.resolve_identity(
                email=extracted_email,
                phone=ticket.customer_phone,
            )

    store.get_or_create_customer(
        key=customer_key,
        name=ticket.customer_name,
        channel=ticket.channel.value,
    )
    conversation = store.get_or_create_conversation(
        customer_key=customer_key,
        channel=ticket.channel.value,
    )
    conversation_context = store.get_conversation_context(customer_key)
    prior_topic = store.has_prior_topic(customer_key, ticket.inferred_topic)

    # Step 2: Search knowledge base
    kb_results = _kb.search(ticket.inferred_topic + " " + ticket.message[:200])

    # Step 3: Evaluate escalation (always — never skip)
    escalation = evaluate_escalation(ticket.message)

    # Step 4: Short-circuit on escalation — skip LLM generation
    if escalation.should_escalate:
        raw = _ESCALATION_ACK_TEMPLATE
        formatted = format_response(raw, ticket.channel, ticket.customer_first_name)
        elapsed = time.monotonic() * 1000 - start_ms
        from src.agent.prompts import get_system_prompt as _gsp
        dt_str = _gsp(ticket.channel.value, ticket.customer_first_name).split("Current date and time: ")[1].split("\n")[0]

        # T016: Record state — escalation path
        inbound_msg = _make_inbound_message(ticket, escalation, dt_str)
        store.add_message(conversation.id, inbound_msg)
        store.add_topic(conversation.id, ticket.inferred_topic)
        if conversation.ticket.status in (TicketStatus.OPEN, TicketStatus.PENDING):
            store.transition_ticket(conversation.id, TicketStatus.ESCALATED)  # T033
        outbound_msg = _make_outbound_message(raw, ticket.channel, dt_str)
        store.add_message(conversation.id, outbound_msg)

        return AgentResponse(
            ticket_id=ticket.ticket_id,
            channel=ticket.channel,
            raw_response=raw,
            formatted_response=formatted,
            escalation=escalation,
            kb_results_used=[],
            processing_time_ms=round(elapsed, 2),
            model_used="none (escalated)",
            prompt_datetime=dt_str,
        )

    # Step 5: Generate response via OpenAI
    system_prompt = get_system_prompt(ticket.channel.value, ticket.customer_first_name)
    dt_str = system_prompt.split("Current date and time: ")[1].split("\n")[0]

    kb_context = "\n\n".join(
        f"[{r.section_title}]\n{r.content}" for r in kb_results if r.relevance_score > 0
    )

    # T038: Build prior-topic note
    prior_note = ""
    if prior_topic:
        count = store.count_topic_contacts(customer_key, ticket.inferred_topic)
        prior_note = (
            f"\n\nNote: This customer has contacted us about '{ticket.inferred_topic}' "
            f"{count} time(s) before. Skip basic troubleshooting steps already attempted."
        )

    history_note = f"\n\nConversation so far:\n{conversation_context}" if conversation_context else ""

    user_content = ticket.message
    if kb_context:
        user_content = (
            f"Knowledge base context:\n{kb_context}"
            f"{history_note}{prior_note}\n\n---\nCustomer message:\n{ticket.message}"
        )
    elif history_note or prior_note:
        user_content = f"{ticket.message}{history_note}{prior_note}"

    client = _get_openai()
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        temperature=0.3,
        max_tokens=500,
    )

    raw_response = completion.choices[0].message.content or ""

    # Step 6: Format for channel
    formatted = format_response(raw_response, ticket.channel, ticket.customer_first_name)

    elapsed = time.monotonic() * 1000 - start_ms

    # T016: Record state — normal path
    inbound_msg = _make_inbound_message(ticket, escalation, dt_str)
    store.add_message(conversation.id, inbound_msg)
    store.add_topic(conversation.id, ticket.inferred_topic)  # T038
    if conversation.ticket.status == TicketStatus.OPEN:
        store.transition_ticket(conversation.id, TicketStatus.PENDING)
    outbound_msg = _make_outbound_message(raw_response, ticket.channel, dt_str)
    store.add_message(conversation.id, outbound_msg)

    return AgentResponse(
        ticket_id=ticket.ticket_id,
        channel=ticket.channel,
        raw_response=raw_response,
        formatted_response=formatted,
        escalation=escalation,
        kb_results_used=kb_results,
        processing_time_ms=round(elapsed, 2),
        model_used="gpt-4o-mini",
        prompt_datetime=dt_str,
    )


# ---------------------------------------------------------------------------
# T011 — CLI runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json as _json

    with open(Path(__file__).parent.parent.parent / "context" / "sample-tickets.json") as f:
        raw_tickets = _json.load(f)

    ticket_ids = ["TKT-002", "TKT-006", "TKT-025", "TKT-032", "TKT-044"]
    tickets_by_id = {t["id"]: t for t in raw_tickets}

    for tid in ticket_ids:
        raw = tickets_by_id[tid]
        msg = TicketMessage(
            id=raw["id"],
            channel=Channel(raw["channel"]),
            customer_name=raw["customer_name"],
            customer_email=raw.get("customer_email"),
            customer_phone=raw.get("customer_phone"),
            subject=raw.get("subject"),
            message=raw["message"],
            received_at=raw.get("timestamp", raw.get("received_at", "")),
            metadata={},
            category=raw.get("category"),
        )

        print(f"\n{'='*50}")
        print(f"=== {tid} ({raw['channel']}) ===")
        print(f"From: {raw['customer_name']}")
        print(f"{'='*50}")

        response = process_ticket(msg)

        print(f"Escalated: {response.escalation.should_escalate}")
        if response.escalation.should_escalate:
            print(f"Urgency: {response.escalation.urgency}")
            print(f"Reason: {response.escalation.reason}")
        else:
            print(f"Response length: {len(response.formatted_response)} chars")
            print(f"Response preview: {response.formatted_response[:120]}...")
        print(f"Processing time: {response.processing_time_ms:.0f}ms")
        print(f"Datetime injected: {response.prompt_datetime}")
