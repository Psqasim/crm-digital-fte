"""
production/api/chat_routes.py
Phase 7B: POST /chat/message — NexaFlow AI chat widget endpoint.

Request flow (order is enforced — HIGH RISK):
1. Sanitize + length check (400 on failure)
2. Injection pattern check (422 on detection) — BEFORE session lookup
3. Session lookup / creation
4. Rate limit check (429 when count > 20) — BEFORE Runner.run()
5. input_items assembly (manual multi-turn pattern, R-001)
6. Runner.run(agent, input_items, max_turns=5)
7. Session input_items update + trim to last 20
8. Return ChatMessageResponse

Isolation: This endpoint NEVER creates tickets, publishes Kafka events,
or writes to the database (FR-022 — chat is stateless self-service).
"""

from __future__ import annotations

import sys

from agents import Runner
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from production.chat.chat_agent import build_chat_agent
from production.chat.sanitizer import check_injection, sanitize_message
from production.chat.schemas import ChatMessageRequest, ChatMessageResponse
from production.chat.session_store import get_or_create_session, increment_and_get_result

router = APIRouter(prefix="/chat", tags=["chat"])

# Max input_items to retain per session (10 turns = 20 items: 10 user + 10 assistant)
_MAX_INPUT_ITEMS = 20


@router.post("/message", response_model=ChatMessageResponse)
async def send_chat_message(request: ChatMessageRequest) -> ChatMessageResponse:
    """Process a single chat turn and return the AI reply.

    Security checks occur before any session lookup or AI call:
    1. HTML sanitisation + length validation (400)
    2. Prompt injection detection (422)
    3. Rate limit enforcement (429)
    """
    # --- Step 1: Sanitise + length check ---
    sanitized = sanitize_message(request.message)
    if not sanitized:
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    if len(sanitized) > 500:
        raise HTTPException(status_code=400, detail="Message too long (max 500 characters)")

    # --- Step 2: Injection check (BEFORE session lookup) --- HIGH RISK ordering
    if check_injection(sanitized):
        raise HTTPException(
            status_code=422,
            detail="I can't process that request. Please keep questions about NexaFlow support.",
        )

    # --- Step 3: Session lookup / creation ---
    session = get_or_create_session(request.session_id)

    # --- Step 4: Rate limit check (BEFORE Runner.run()) --- HIGH RISK ordering
    rl = increment_and_get_result(session)
    if not rl.allowed:
        raise HTTPException(
            status_code=429,
            detail="Session limit reached. Please submit a formal support ticket for continued assistance.",
        )

    # --- Step 5: Assemble input_items (manual multi-turn, R-001) --- HIGH RISK
    # Convert frontend display history to SDK input format
    history_items = [
        {"role": msg.role, "content": msg.content}
        for msg in request.history
    ]
    # Append the new user message
    new_user_item = {"role": "user", "content": sanitized}

    if session.input_items:
        # Subsequent turn: use accumulated SDK input_items + new message
        input_items = session.input_items + [new_user_item]
    else:
        # First turn: build from frontend history + new message
        input_items = history_items + [new_user_item]

    # --- Step 6: Runner.run() --- HIGH RISK
    try:
        agent = build_chat_agent()
        result = await Runner.run(agent, input_items, max_turns=5)
        reply = result.final_output or "I had trouble processing that. Please try again."
    except Exception as e:
        print(f"[chat] Runner.run error: {e}", file=sys.stderr)
        return ChatMessageResponse(
            reply="I'm having trouble connecting. Please try again or use our support form.",
            session_id=session.session_id,
            warning=rl.warning,
        )

    # --- Step 7: Update session input_items (trim to last 20) ---
    session.input_items = result.to_input_list()[-_MAX_INPUT_ITEMS:]

    # --- Step 8: Return response ---
    return ChatMessageResponse(
        reply=reply,
        session_id=session.session_id,
        warning=rl.warning,
    )
