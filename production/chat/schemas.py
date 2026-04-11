"""
production/chat/schemas.py
Phase 7B: Pydantic v2 request/response models for POST /chat/message.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class HistoryMessage(BaseModel):
    """Single message in the conversation history sent by the frontend."""

    role: Literal["user", "assistant"]
    content: str


class ChatMessageRequest(BaseModel):
    """Request body for POST /chat/message."""

    message: str = Field(min_length=1, max_length=500)
    session_id: str = Field(default="")
    history: list[HistoryMessage] = Field(default_factory=list, max_length=20)


class ChatMessageResponse(BaseModel):
    """Response body for POST /chat/message."""

    reply: str
    session_id: str
    warning: str | None = None
