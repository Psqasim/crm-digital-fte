"""
production/api/webhooks.py
Phase 4C: FastAPI webhook endpoints for Gmail (Pub/Sub) and WhatsApp (Twilio).

Rules:
- Gmail endpoint: malformed JSON → 400; any internal error → 200 (no 5xx)
- WhatsApp endpoint: missing/invalid signature → 403; any other error → 200
- NEVER return 5xx from either endpoint (prevents retry storms)
"""

from __future__ import annotations

import json
import sys

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()


# ---------------------------------------------------------------------------
# Helper: reconstruct URL respecting X-Forwarded-Proto (T025)
# ---------------------------------------------------------------------------


def reconstruct_url(request: Request) -> str:
    """Return the canonical URL of the request, honouring X-Forwarded-Proto.

    Twilio always signs requests with https://. When running behind ngrok or
    a reverse proxy, the actual scheme seen by FastAPI may be http, so we
    must reconstruct the https:// URL to match Twilio's signature.
    """
    forwarded_proto = request.headers.get("X-Forwarded-Proto", "")
    if forwarded_proto == "https":
        host = request.headers.get("host", request.url.hostname)
        return f"https://{host}{request.url.path}"
    return str(request.url)


# ---------------------------------------------------------------------------
# POST /webhooks/gmail — Gmail Pub/Sub push endpoint (T024)
# ---------------------------------------------------------------------------


@router.post("/webhooks/gmail")
async def gmail_webhook(request: Request) -> JSONResponse:
    """Receive a Gmail Pub/Sub push notification and enqueue a TicketMessage.

    Returns HTTP 400 for malformed JSON; HTTP 200 for all other outcomes
    (including internal errors) to prevent Pub/Sub retry storms.
    """
    # Parse JSON body — malformed → 400
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "parse_error"}, status_code=400)

    # Process notification — all errors caught → 200
    try:
        from production.channels.gmail_handler import _get_handler
        handler = _get_handler()
        await handler.process_pub_sub_push(body)
        return JSONResponse({"status": "ok"})
    except Exception as e:
        print(f"[webhooks/gmail] ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return JSONResponse({"status": "error_logged"}, status_code=200)


# ---------------------------------------------------------------------------
# POST /webhooks/whatsapp — Twilio WhatsApp webhook endpoint (T042)
# ---------------------------------------------------------------------------


@router.post("/webhooks/whatsapp")
async def whatsapp_webhook(request: Request) -> JSONResponse:
    """Receive a Twilio WhatsApp webhook and enqueue a TicketMessage.

    Returns HTTP 403 for missing/invalid Twilio signature.
    Returns HTTP 200 for all other outcomes (including Kafka failures).
    NEVER returns 5xx.
    """
    try:
        from production.channels.whatsapp_handler import WhatsAppHandler, _get_handler as _get_wa_handler

        # Extract Twilio signature
        signature = request.headers.get("X-Twilio-Signature", "")
        if not signature:
            return JSONResponse({"error": "missing_signature"}, status_code=403)

        # Parse form body
        form_data = await request.form()
        post_params = dict(form_data)

        # Reconstruct URL (handles X-Forwarded-Proto for ngrok)
        url = reconstruct_url(request)

        # Validate Twilio signature
        wa_handler = _get_wa_handler()
        if not wa_handler.validate_signature(url, post_params, signature):
            return JSONResponse({"error": "invalid_signature"}, status_code=403)

        # Process webhook — Kafka failures must not break response
        try:
            await wa_handler.process_webhook(post_params)
        except Exception as inner_e:
            print(f"[webhooks/whatsapp] process error: {type(inner_e).__name__}: {inner_e}", file=sys.stderr)

        return JSONResponse({"status": "ok"})

    except Exception as e:
        print(f"[webhooks/whatsapp] ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return JSONResponse({"status": "error_logged"}, status_code=200)
