from __future__ import annotations

import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

from openai import OpenAI

from src.agent.channel_formatter import format_response
from src.agent.escalation_evaluator import evaluate_escalation
from src.agent.knowledge_base import KnowledgeBase
from src.agent.models import (
    AgentResponse,
    Channel,
    EscalationDecision,
    KBResult,
    NormalizedTicket,
    TicketMessage,
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

    user_content = ticket.message
    if kb_context:
        user_content = f"Knowledge base context:\n{kb_context}\n\n---\nCustomer message:\n{ticket.message}"

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
