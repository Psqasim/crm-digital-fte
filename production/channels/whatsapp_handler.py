"""
production/channels/whatsapp_handler.py
Phase 4C + 7D: WhatsApp channel handler — Twilio webhook → DB → AI agent → reply.

Flow:
  1. Twilio webhook POST → /webhooks/whatsapp
  2. HMAC-SHA1 signature validated via RequestValidator
  3. process_webhook() deduplicates by MessageSid, writes ticket directly to DB
  4. AI agent processes ticket, generates reply
  5. send_reply() sends outbound WhatsApp message via Twilio REST API
"""

from __future__ import annotations

import os
import sys
from typing import Any

from twilio.request_validator import RequestValidator

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

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
    # Signature validation
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
    # Process incoming webhook
    # ------------------------------------------------------------------

    async def process_webhook(self, payload: dict) -> None:
        """Process a Twilio WhatsApp webhook payload.

        Writes ticket directly to DB (bypasses Kafka), runs AI agent,
        sends reply back to customer via WhatsApp.

        Returns None always (result handled in-process via send_reply).
        """
        try:
            message_sid = payload.get("MessageSid", "")
            if not message_sid:
                print("[whatsapp_handler] WARNING: payload missing MessageSid", file=sys.stderr)
                return None

            # --- Lazy imports to avoid circular dependencies ---
            from production.database.queries import get_db_pool  # noqa: PLC0415
            from production.database import queries  # noqa: PLC0415

            pool = await get_db_pool()

            # Idempotency gate — DB-level claim works across all uvicorn workers
            claimed = await queries.claim_whatsapp_message(pool, message_sid)
            if not claimed:
                print(f"[whatsapp_handler] duplicate MessageSid {message_sid} — skipping", file=sys.stderr)
                return None

            # Extract and normalise fields
            from_raw = payload.get("From", "")
            customer_phone = from_raw.replace("whatsapp:", "").strip()
            body_text = payload.get("Body", "").strip()
            num_media = int(payload.get("NumMedia", "0"))

            if not body_text:
                message_text = "[media attachment — no text]" if num_media > 0 else "[empty message]"
            else:
                message_text = body_text

            # Use phone as pseudo-email for DB customer lookup/creation
            clean_phone = customer_phone.lstrip("+").replace(" ", "")
            pseudo_email = f"wa_{clean_phone}@whatsapp.nexaflow"
            customer = await queries.get_or_create_customer(pool, pseudo_email, name=customer_phone)
            if customer is None:
                print("[whatsapp_handler] ERROR: could not get/create customer", file=sys.stderr)
                return None
            customer_id = str(customer["id"])

            # Link phone identifier (idempotent upsert)
            await queries.link_phone_to_customer(pool, customer_id, customer_phone)

            # Create conversation → add customer message → create ticket
            conversation_id = await queries.create_conversation(pool, customer_id, "whatsapp")
            if not conversation_id:
                print("[whatsapp_handler] ERROR: could not create conversation", file=sys.stderr)
                return None

            await queries.add_message(
                pool, conversation_id,
                role="customer", content=message_text, channel="whatsapp",
            )

            internal_ticket_id = await queries.create_ticket(
                pool, conversation_id, customer_id, channel="whatsapp",
                subject=message_text[:100],
            )
            if not internal_ticket_id:
                print("[whatsapp_handler] ERROR: could not create ticket", file=sys.stderr)
                return None

            # Reload full ticket dict for agent processing
            ticket = await queries.get_ticket_by_display_id(pool, internal_ticket_id)
            if not ticket:
                return None

            # Run AI agent — saves response to DB, updates ticket status
            from production.api.agent_routes import _run_agent_on_ticket  # noqa: PLC0415
            agent_resp = await _run_agent_on_ticket(pool, ticket)

            # Send AI reply back to customer via WhatsApp
            if agent_resp and agent_resp.response_text:
                await self.send_reply(customer_phone, agent_resp.response_text)
                print(
                    f"[whatsapp_handler] replied to {customer_phone} "
                    f"for ticket {ticket['ticket_id']}",
                    file=sys.stderr,
                )
            else:
                print(
                    f"[whatsapp_handler] WARNING: no agent response for {ticket['ticket_id']}",
                    file=sys.stderr,
                )

            return None

        except Exception as e:
            print(f"[whatsapp_handler] ERROR in process_webhook: {type(e).__name__}: {e}", file=sys.stderr)
            return None

    # ------------------------------------------------------------------
    # Send outbound reply
    # ------------------------------------------------------------------

    async def send_reply(self, to_phone: str, body: str) -> Any:
        """Send a WhatsApp message via Twilio REST API.

        Returns the Twilio message SID string on success, or a dict with
        delivery_status='failed' on error.
        """
        try:
            if self.twilio_client is None:
                raise RuntimeError("Twilio client not initialised — check TWILIO credentials")

            from_number = os.environ.get("TWILIO_WHATSAPP_NUMBER", "").strip()
            message = self.twilio_client.messages.create(
                to=f"whatsapp:{to_phone}",
                from_=from_number,
                body=body[:1600],
            )
            return message.sid
        except Exception as e:
            print(f"[whatsapp_handler] ERROR in send_reply: {type(e).__name__}: {e}", file=sys.stderr)
            return {"delivery_status": "failed", "error": str(e)}
