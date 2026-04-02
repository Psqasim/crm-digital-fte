from __future__ import annotations

from src.agent.models import Channel

_NEXAFLOW_SIGNATURE = """
---
NexaFlow Customer Success
support@nexaflow.io | help.nexaflow.io
Mon–Fri 9am–6pm PKT | AI support available 24/7"""

_EMAIL_HARD_LIMIT = 2500
_WHATSAPP_HARD_LIMIT = 1600
_WHATSAPP_SOFT_LIMIT = 300
_WEBFORM_HARD_LIMIT = 5000


def format_response(raw: str, channel: Channel, name: str) -> str:
    if channel == Channel.EMAIL:
        return _format_email(raw, name)
    elif channel == Channel.WHATSAPP:
        return _format_whatsapp(raw, name)
    elif channel == Channel.WEB_FORM:
        return _format_web_form(raw, name)
    return raw


def _format_email(raw: str, name: str) -> str:
    body = raw.strip()
    greeting = f"Dear {name},"
    response = f"{greeting}\n\n{body}{_NEXAFLOW_SIGNATURE}"
    if len(response) > _EMAIL_HARD_LIMIT:
        # Truncate body to fit
        available = _EMAIL_HARD_LIMIT - len(greeting) - len(_NEXAFLOW_SIGNATURE) - 4
        body = body[:available].rstrip() + "…"
        response = f"{greeting}\n\n{body}{_NEXAFLOW_SIGNATURE}"
    return response


def _format_whatsapp(raw: str, name: str) -> str:
    greeting = f"Hi {name}! 👋"
    body = raw.strip()

    # Limit to 3 sentences
    sentences = _split_sentences(body)
    if len(sentences) > 3:
        body = " ".join(sentences[:3])

    response = f"{greeting} {body}"

    if len(response) > _WHATSAPP_HARD_LIMIT:
        available = _WHATSAPP_HARD_LIMIT - len(greeting) - 2
        response = f"{greeting} {body[:available].rstrip()}…"

    return response


def _format_web_form(raw: str, name: str) -> str:
    body = raw.strip()
    greeting = f"Hi {name},"
    response = f"{greeting}\n\n{body}"
    if len(response) > _WEBFORM_HARD_LIMIT:
        available = _WEBFORM_HARD_LIMIT - len(greeting) - 4
        body = body[:available].rstrip() + "…"
        response = f"{greeting}\n\n{body}"
    return response


def _split_sentences(text: str) -> list[str]:
    import re
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]
