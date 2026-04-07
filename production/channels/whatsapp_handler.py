"""
production/channels/whatsapp_handler.py
Phase 4C: WhatsApp channel handler — Twilio webhook → TicketMessage → Kafka.

Flow:
  1. Twilio webhook POST → /webhooks/whatsapp
  2. HMAC-SHA1 signature validated via RequestValidator
  3. process_webhook() deduplicates by MessageSid, normalises to TicketMessage
  4. publish_ticket() sends to Kafka 'fte.tickets.incoming'
  5. send_reply() sends outbound WhatsApp message via Twilio REST API
"""

from __future__ import annotations

import os
import sys
import uuid
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from twilio.request_validator import RequestValidator

from production.channels.kafka_producer import publish_ticket
from src.agent.models import Channel, TicketMessage

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

_seen_message_sids: set[str] = set()

# Module-level singleton handler (used by webhooks endpoint)
_handler_instance: "WhatsAppHandler | None" = None


def _get_handler() -> "WhatsAppHandler":
    """Return (or create) the module-level WhatsAppHandler singleton."""
    global _handler_instance
    if _handler_instance is None:
        _handler_instance = WhatsAppHandler()
    return _handler_instance


# ---------------------------------------------------------------------------
# WhatsAppHandler class
# ---------------------------------------------------------------------------


class WhatsAppHandler:
    """Handles Twilio WhatsApp webhooks and outbound message sending."""

    def __init__(self) -> None:
        # Lazy Twilio client: credentials read from env, None if missing
        account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        auth_token = os.environ.get("TWILIO_AUTH_TOKEN")

        if account_sid and auth_token:
            try:
                from twilio.rest import Client
                self.twilio_client: Any = Client(account_sid, auth_token)
            except Exception as e:
                print(f"[whatsapp_handler] WARNING: could not init Twilio client: {e}", file=sys.stderr)
                self.twilio_client = None
        else:
            self.twilio_client = None

    # ------------------------------------------------------------------
    # Signature validation (T038 HIGH RISK)
    # ------------------------------------------------------------------

    def validate_signature(self, url: str, post_data: dict, signature: str) -> bool:
        """Validate Twilio HMAC-SHA1 webhook signature.

        Returns False (never raises) if:
        - TWILIO_AUTH_TOKEN env var is missing
        - Signature does not match
        """
        try:
            auth_token = os.environ.get("TWILIO_AUTH_TOKEN", "")
            validator = RequestValidator(auth_token)
            return bool(validator.validate(url, post_data, signature))
        except KeyError:
            print("[whatsapp_handler] WARNING: KeyError in validate_signature", file=sys.stderr)
            return False
        except Exception as e:
            print(f"[whatsapp_handler] ERROR in validate_signature: {type(e).__name__}: {e}", file=sys.stderr)
            return False

    # ------------------------------------------------------------------
    # Process incoming webhook (T039)
    # ------------------------------------------------------------------

    async def process_webhook(self, payload: dict) -> TicketMessage | None:
        """Process a Twilio WhatsApp webhook payload.

        Returns:
        - TicketMessage on success
        - None if duplicate MessageSid (idempotency gate)
        """
        try:
            message_sid = payload.get("MessageSid", "")
            if not message_sid:
                print("[whatsapp_handler] WARNING: payload missing MessageSid", file=sys.stderr)
                return None

            # Idempotency gate
            if message_sid in _seen_message_sids:
                return None

            # Extract and normalise fields
            from_raw = payload.get("From", "")
            customer_phone = from_raw.replace("whatsapp:", "").strip()

            body_text = payload.get("Body", "").strip()
            num_media = int(payload.get("NumMedia", "0"))

            if not body_text:
                if num_media > 0:
                    message_text = "[media attachment — no text]"
                else:
                    message_text = "[empty message]"
            else:
                message_text = body_text

            ticket = TicketMessage(
                id=str(uuid.uuid4()),
                channel=Channel.WHATSAPP,
                customer_name=customer_phone,
                customer_email=None,
                customer_phone=customer_phone,
                subject=None,
                message=message_text,
                received_at=datetime.now(ZoneInfo("Asia/Karachi")).isoformat(),
                metadata={"message_sid": message_sid},
            )

            await publish_ticket(ticket)
            _seen_message_sids.add(message_sid)
            return ticket

        except Exception as e:
            print(f"[whatsapp_handler] ERROR in process_webhook: {type(e).__name__}: {e}", file=sys.stderr)
            return None

    # ------------------------------------------------------------------
    # Send outbound reply (T040)
    # ------------------------------------------------------------------

    async def send_reply(self, to_phone: str, body: str) -> Any:
        """Send a WhatsApp message via Twilio REST API.

        Returns the Twilio message SID string on success, or a dict with
        delivery_status='failed' on error.
        """
        try:
            if self.twilio_client is None:
                raise RuntimeError("Twilio client not initialised — check TWILIO credentials")

            from_number = os.environ.get("TWILIO_WHATSAPP_NUMBER", "")
            message = self.twilio_client.messages.create(
                to=f"whatsapp:{to_phone}",
                from_=from_number,
                body=body[:1600],
            )
            return message.sid
        except Exception as e:
            print(f"[whatsapp_handler] ERROR in send_reply: {type(e).__name__}: {e}", file=sys.stderr)
            return {"delivery_status": "failed", "error": str(e)}
