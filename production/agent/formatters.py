"""
production/agent/formatters.py
Phase 4B: Channel-specific response formatters.

Ported from src/agent/channel_formatter.py with updated limits per spec §Guardrails:
  - Email: ≤ 500 words (not 2500 chars)
  - WhatsApp: ≤ 1600 chars (hard), 3 sentences preferred
  - Web Form: ≤ 1000 chars / 300 words (whichever first)

No import of Channel enum from src/agent/models.py — uses plain strings to avoid
cross-module dependencies.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Signature block
# ---------------------------------------------------------------------------

_NEXAFLOW_SIGNATURE = (
    "\n\n---\n"
    "NexaFlow Customer Success\n"
    "support@nexaflow.io | help.nexaflow.io\n"
    "Mon–Fri 9am–6pm PKT | AI support available 24/7"
)

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class FormattedResponse:
    """Output of a channel formatter function."""

    formatted_text: str
    channel: str
    formatting_notes: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences on '.', '!', '?' boundaries.

    Ported unchanged from src/agent/channel_formatter.py.
    """
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]


def _word_count(text: str) -> int:
    return len(text.split())


# ---------------------------------------------------------------------------
# Public formatters
# ---------------------------------------------------------------------------


def format_email_response(text: str, customer_name: str) -> FormattedResponse:
    """Format a response for email delivery.

    - Prepends "Dear [FirstName]," unless already present.
    - Appends NexaFlow signature unless already present.
    - Truncates body to ≤ 500 words (spec NEVER-6).

    Args:
        text: Raw response body (no greeting, no sign-off).
        customer_name: Customer full name; first name extracted automatically.

    Returns:
        FormattedResponse with channel="email".
    """
    first_name = customer_name.split()[0]
    notes: list[str] = []

    body = text.strip()

    # Greeting
    greeting = f"Dear {first_name},"
    if not body.startswith(greeting):
        body = f"{greeting}\n\n{body}"
        notes.append("added_greeting")

    # Word-count enforcement — count body words only (before signature)
    # Split on greeting to isolate body words
    body_words = body.split()
    # 500-word limit: include greeting words in count
    if len(body_words) > 500:
        body = " ".join(body_words[:500]).rstrip(",;: ") + "…"
        notes.append("truncated_to_500_words")

    # Signature
    if _NEXAFLOW_SIGNATURE.strip() not in body:
        body = body + _NEXAFLOW_SIGNATURE
        notes.append("added_signature")

    return FormattedResponse(formatted_text=body, channel="email", formatting_notes=notes)


def format_whatsapp_response(text: str, customer_name: str) -> FormattedResponse:
    """Format a response for WhatsApp delivery.

    - Prepends "Hi [FirstName]! 👋" unless already present.
    - Strips markdown headers (# / ##) and unordered list markers (- / *).
    - Limits to 3 sentences (spec NEVER-6 preferred length).
    - Hard truncates at 1600 chars.

    Args:
        text: Raw response body.
        customer_name: Customer full name; first name extracted automatically.

    Returns:
        FormattedResponse with channel="whatsapp".
    """
    first_name = customer_name.split()[0]
    notes: list[str] = []

    body = text.strip()

    # Strip markdown headers
    body = re.sub(r"^#{1,6}\s+", "", body, flags=re.MULTILINE)
    # Strip unordered list markers
    body = re.sub(r"^[-*]\s+", "", body, flags=re.MULTILINE)
    body = body.strip()

    # 3-sentence limit
    sentences = _split_sentences(body)
    if len(sentences) > 3:
        body = " ".join(sentences[:3])
        notes.append("truncated_to_3_sentences")

    # Greeting
    greeting = f"Hi {first_name}! 👋"
    if not body.startswith(greeting):
        response = f"{greeting} {body}"
        notes.append("added_greeting")
    else:
        response = body

    # Hard 1600-char limit — truncate at last complete sentence
    if len(response) > 1600:
        available = 1600 - len(greeting) - 2
        truncated = body[:available]
        # Walk back to last sentence boundary
        last_boundary = max(
            truncated.rfind("."),
            truncated.rfind("!"),
            truncated.rfind("?"),
        )
        if last_boundary > 0:
            truncated = truncated[: last_boundary + 1]
        response = f"{greeting} {truncated.rstrip()}"
        notes.append("truncated_at_1600_chars")

    return FormattedResponse(
        formatted_text=response, channel="whatsapp", formatting_notes=notes
    )


def format_web_form_response(text: str, customer_name: str) -> FormattedResponse:
    """Format a response for the web support form.

    - Prepends "Hi [FirstName]," unless already present.
    - Allows light markdown (bold **text**, short bullet lists).
    - Truncates at 1000 chars or 300 words (whichever is reached first).

    Args:
        text: Raw response body.
        customer_name: Customer full name; first name extracted automatically.

    Returns:
        FormattedResponse with channel="web_form".
    """
    first_name = customer_name.split()[0]
    notes: list[str] = []

    body = text.strip()

    # Greeting
    greeting = f"Hi {first_name},"
    if not body.startswith(greeting):
        body = f"{greeting}\n\n{body}"
        notes.append("added_greeting")

    # Word-count truncation (300 words)
    words = body.split()
    if len(words) > 300:
        body = " ".join(words[:300]).rstrip(",;: ") + "…"
        notes.append("truncated_to_300_words")

    # Char truncation (1000 chars)
    if len(body) > 1000:
        body = body[:1000].rstrip() + "…"
        notes.append("truncated_at_1000_chars")

    return FormattedResponse(formatted_text=body, channel="web_form", formatting_notes=notes)
