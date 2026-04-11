"""
production/chat/session_store.py
Phase 7B: In-memory session store for the chat widget.

Design: module-level dict keyed by session_id UUID.
Single-process HF Spaces deployment — asyncio event loop serialises requests
so no locking is required (same pattern as ADR-0001 ticket registry).
Sessions are ephemeral — cleared on server restart (FR-022, spec assumption 3).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class ChatSession:
    """One user's chat conversation.

    input_items accumulates the OpenAI Agents SDK turn history.
    Trimmed to last 20 items (10 turns) to control token usage.
    """

    session_id: str
    input_items: list = field(default_factory=list)
    message_count: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class SessionRateLimitResult:
    """Result of a rate-limit check after incrementing message_count."""

    allowed: bool
    warning: str | None
    count: int


# ---------------------------------------------------------------------------
# Module-level in-memory store
# ---------------------------------------------------------------------------

_sessions: dict[str, ChatSession] = {}


def get_or_create_session(session_id: str) -> ChatSession:
    """Return existing session or create a new one.

    Pass session_id="" (empty string) to force creation of a fresh session.
    Returns the session object (caller must not mutate session_id).
    """
    if not session_id or session_id not in _sessions:
        new_id = str(uuid.uuid4())
        session = ChatSession(session_id=new_id)
        _sessions[new_id] = session
        return session
    return _sessions[session_id]


def increment_and_get_result(session: ChatSession) -> SessionRateLimitResult:
    """Increment message_count and evaluate rate-limit state.

    Returns:
        SessionRateLimitResult with:
        - allowed=False when count >= 20 (hard limit)
        - warning set at count == 18 or 19 (soft warning)
    """
    session.message_count += 1
    count = session.message_count

    if count > 20:
        return SessionRateLimitResult(allowed=False, warning=None, count=count)

    if count == 20:
        # 20th message is allowed; but this is the last one
        return SessionRateLimitResult(allowed=True, warning=None, count=count)

    if count == 19:
        return SessionRateLimitResult(
            allowed=True,
            warning="You have 1 message remaining in this session.",
            count=count,
        )

    if count == 18:
        return SessionRateLimitResult(
            allowed=True,
            warning="You have 2 messages remaining in this session.",
            count=count,
        )

    return SessionRateLimitResult(allowed=True, warning=None, count=count)


def clear_session(session_id: str) -> None:
    """Remove a session from the store (called on clear-chat or expiry)."""
    _sessions.pop(session_id, None)
