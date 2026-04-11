"""
production/chat/sanitizer.py
Phase 7B: Input sanitisation and prompt-injection detection for the chat endpoint.

sanitize_message: strips HTML tags + whitespace.
check_injection: case-insensitive pattern match against INJECTION_PATTERNS.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# HTML sanitisation
# ---------------------------------------------------------------------------

_HTML_TAG_RE = re.compile(r"<[^>]+>")


def sanitize_message(raw: str) -> str:
    """Strip HTML tags and surrounding whitespace from raw user input."""
    return _HTML_TAG_RE.sub("", raw).strip()


# ---------------------------------------------------------------------------
# Prompt-injection detection
# ---------------------------------------------------------------------------

INJECTION_PATTERNS: list[str] = [
    "ignore previous instructions",
    "ignore your instructions",
    "system prompt",
    "jailbreak",
    "disregard your",
    "forget your instructions",
    "you are now",
    "act as if",
    "pretend you are",
]


def check_injection(text: str) -> bool:
    """Return True if the text matches any known prompt-injection pattern.

    Check is case-insensitive. Returns False for normal user messages.
    """
    lower = text.lower()
    return any(pattern in lower for pattern in INJECTION_PATTERNS)
