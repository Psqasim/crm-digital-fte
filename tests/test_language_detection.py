"""
tests/test_language_detection.py
Phase 7B: Integration tests for multilingual support.

These tests call the REAL agent with REAL OpenAI API.
They are skipped automatically in CI if OPENAI_API_KEY is not set.

Run locally with:
  OPENAI_API_KEY=sk-... pytest tests/test_language_detection.py -v -m integration

Tests:
1. test_urdu_input_urdu_response — Urdu message → Urdu characters in response
2. test_english_input_english_response — English message → printable ASCII
"""
from __future__ import annotations

import os

import pytest


# Skip if no API key (CI safe)
pytestmark = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set — skipping integration tests",
)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_urdu_input_urdu_response():
    """Urdu message → response contains Urdu (non-ASCII) characters."""
    from production.chat.chat_agent import build_chat_agent
    from production.chat.sanitizer import sanitize_message
    from agents import Runner

    message = "میں NexaFlow کو Slack سے کیسے جوڑوں؟"
    sanitized = sanitize_message(message)

    agent = build_chat_agent()
    result = await Runner.run(agent, [{"role": "user", "content": sanitized}], max_turns=3)

    reply = result.final_output or ""
    # Urdu response must contain at least one non-ASCII character
    assert any(ord(c) > 127 for c in reply), (
        f"Expected Urdu (non-ASCII) characters in response, got: {reply!r}"
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_english_input_english_response():
    """English message → response is primarily printable ASCII/English."""
    from production.chat.chat_agent import build_chat_agent
    from production.chat.sanitizer import sanitize_message
    from agents import Runner

    message = "How do I reset my password in NexaFlow?"
    sanitized = sanitize_message(message)

    agent = build_chat_agent()
    result = await Runner.run(agent, [{"role": "user", "content": sanitized}], max_turns=3)

    reply = result.final_output or ""
    assert len(reply) > 10, "Expected a meaningful English response"
    # Should be mostly ASCII (allow <5% non-ASCII for punctuation/emojis)
    non_ascii = sum(1 for c in reply if ord(c) > 127)
    assert non_ascii / max(len(reply), 1) < 0.05, (
        f"Too many non-ASCII chars in English response: {reply!r}"
    )
