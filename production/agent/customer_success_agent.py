"""
production/agent/customer_success_agent.py
Phase 4B: Agent definition, process_ticket() entry point, AgentResponse parser.

Key design decisions (per ADR-0003 and Context7 research):
- Agent is constructed INSIDE process_ticket() on every call — never a module-level
  singleton — so build_system_prompt() always gets a fresh PKT datetime.
- instructions is called as a string (build_system_prompt evaluated at process_ticket
  call time, which IS runtime, satisfying the ALWAYS-1 datetime injection rule).
- RunResult.final_output is a str; new_items is scanned for tool call outputs to
  extract ticket_id, escalation_id, and resolution_status.
- openai.APIError is retried once; openai.AuthenticationError and
  openai.PermissionDeniedError bubble up (config errors, not transient failures).
"""

from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import dataclass, field

import openai
from agents import Agent, Runner

from production.agent.prompts import build_system_prompt
from production.agent.tools import (
    create_ticket,
    escalate_to_human,
    get_customer_history,
    get_sentiment_trend,
    resolve_ticket,
    search_knowledge_base,
    send_response,
)
from production.database import queries
from production.database.queries import get_db_pool

# ---------------------------------------------------------------------------
# Data types (T015)
# ---------------------------------------------------------------------------


@dataclass
class AgentResponse:
    """Structured output from process_ticket().

    Extends the prototype AgentResponse (src/agent/models.py) with escalation_id.
    """

    ticket_id: str | None = None
    response_text: str = ""
    channel: str = ""
    escalated: bool = False
    escalation_id: str | None = None
    resolution_status: str = "pending"
    error: str | None = None


@dataclass
class CustomerContext:
    """Input bundle for a single agent invocation."""

    customer_id: str
    customer_name: str
    customer_email: str
    channel: str
    message: str
    conversation_id: str | None = None


# ---------------------------------------------------------------------------
# RunResult parser helpers
# ---------------------------------------------------------------------------


def _extract_ticket_id(result) -> str | None:
    """Scan RunResult.new_items for a create_ticket tool call output and return ticket_id."""
    try:
        from agents.items import ToolCallOutputItem  # type: ignore[attr-defined]
        for item in getattr(result, "new_items", []):
            if isinstance(item, ToolCallOutputItem):
                # The item's output is the JSON string returned by the tool
                output_str = getattr(item, "output", None)
                if output_str and isinstance(output_str, str):
                    try:
                        data = json.loads(output_str)
                        if "ticket_id" in data and "error" not in data:
                            return str(data["ticket_id"])
                    except (json.JSONDecodeError, KeyError):
                        pass
    except (ImportError, AttributeError):
        pass
    return None


def _extract_escalation(result) -> tuple[bool, str | None]:
    """Return (escalated: bool, escalation_id: str | None) from RunResult tool calls."""
    try:
        from agents.items import ToolCallOutputItem  # type: ignore[attr-defined]
        for item in getattr(result, "new_items", []):
            if isinstance(item, ToolCallOutputItem):
                output_str = getattr(item, "output", None)
                if output_str and isinstance(output_str, str):
                    try:
                        data = json.loads(output_str)
                        if data.get("status") == "escalated" and "escalation_id" in data:
                            return True, str(data["escalation_id"])
                    except (json.JSONDecodeError, KeyError):
                        pass
    except (ImportError, AttributeError):
        pass
    return False, None


def _extract_resolution_status(result) -> str:
    """Return 'resolved' if resolve_ticket was called successfully, else 'pending'."""
    try:
        from agents.items import ToolCallOutputItem  # type: ignore[attr-defined]
        for item in getattr(result, "new_items", []):
            if isinstance(item, ToolCallOutputItem):
                output_str = getattr(item, "output", None)
                if output_str and isinstance(output_str, str):
                    try:
                        data = json.loads(output_str)
                        if data.get("status") == "resolved" and "error" not in data:
                            return "resolved"
                    except (json.JSONDecodeError, KeyError):
                        pass
    except (ImportError, AttributeError):
        pass
    return "pending"


def _parse_run_result(result, channel: str) -> AgentResponse:
    """Extract AgentResponse from a RunResult.

    Falls back to safe defaults if parsing fails.
    """
    try:
        response_text: str = result.final_output or ""
        ticket_id = _extract_ticket_id(result)
        escalated, escalation_id = _extract_escalation(result)
        resolution_status = _extract_resolution_status(result)

        return AgentResponse(
            ticket_id=ticket_id,
            response_text=response_text,
            channel=channel,
            escalated=escalated,
            escalation_id=escalation_id,
            resolution_status=resolution_status,
            error=None,
        )
    except Exception as e:
        print(f"[_parse_run_result ERROR] {e}", file=sys.stderr)
        return AgentResponse(
            response_text="",
            channel=channel,
            escalated=True,
            error=f"RunResult parse error: {e}",
        )


# ---------------------------------------------------------------------------
# Main entry point (T016, T017, T018, T019)
# ---------------------------------------------------------------------------


async def process_ticket(ctx: CustomerContext) -> AgentResponse:
    """Process a single customer support ticket end-to-end.

    Steps:
    1. Resolve or create customer record (get_or_create_customer).
    2. Create a conversation if ctx.conversation_id is None.
    3. Build channel-aware system prompt with injected PKT datetime.
    4. Construct Agent with all 7 tools (fresh instance each call).
    5. Run agent; retry once on openai.APIError.
    6. Parse RunResult into AgentResponse.

    Args:
        ctx: CustomerContext bundle from the inbound channel handler.

    Returns:
        AgentResponse with ticket_id, response_text, escalation info.

    Raises:
        openai.AuthenticationError: API key is invalid (not retried).
        openai.PermissionDeniedError: Insufficient permissions (not retried).
    """
    # ---- Step 1: Resolve customer ----
    pool = await get_db_pool()
    customer_row = await queries.get_or_create_customer(
        pool, ctx.customer_email, ctx.customer_name
    )
    if customer_row:
        customer_id = str(customer_row["id"])
    else:
        customer_id = ctx.customer_id  # fallback to context value

    # ---- Step 2: Conversation ----
    conversation_id = ctx.conversation_id
    if conversation_id is None:
        conversation_id = await queries.create_conversation(pool, customer_id, ctx.channel)

    # ---- Step 3: Build system prompt (PKT datetime injected here) ----
    system_prompt = build_system_prompt(ctx.channel, ctx.customer_name)

    # ---- Step 4: Construct Agent (T016 — inside function, not module-level) ----
    agent = Agent(
        name="NexaFlow Customer Success",
        instructions=system_prompt,
        model="gpt-4o-mini",
        tools=[
            search_knowledge_base,
            create_ticket,
            get_customer_history,
            escalate_to_human,
            send_response,
            get_sentiment_trend,
            resolve_ticket,
        ],
    )

    # ---- Step 5: Runner.run() with retry (T017) ----
    try:
        result = await Runner.run(agent, ctx.message, max_turns=10)
    except (openai.AuthenticationError, openai.PermissionDeniedError):
        raise  # config errors — do not retry or swallow
    except openai.APIError as e:
        print(f"[process_ticket] First APIError: {e} — retrying once", file=sys.stderr)
        await asyncio.sleep(2)
        try:
            result = await Runner.run(agent, ctx.message, max_turns=10)
        except openai.APIError as e2:
            print(f"[process_ticket] Second APIError: {e2} — escalating", file=sys.stderr)
            # Best-effort escalation (no ticket_id yet if create_ticket wasn't called)
            return AgentResponse(
                ticket_id=None,
                response_text="",
                channel=ctx.channel,
                escalated=True,
                error=str(e2),
                resolution_status="error",
            )

    # ---- Step 6: Parse RunResult → AgentResponse (T018) ----
    return _parse_run_result(result, ctx.channel)
