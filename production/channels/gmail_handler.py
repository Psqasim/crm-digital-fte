"""
production/channels/gmail_handler.py
Phase 4C: Gmail channel handler — Pub/Sub push → TicketMessage → Kafka.

Flow:
  1. Gmail Pub/Sub push notification → /webhooks/gmail
  2. process_pub_sub_push() decodes historyId, deduplicates, calls history.list
  3. For each new message: fetch full content → build TicketMessage → publish_ticket()
  4. send_reply() sends a threaded Gmail reply back to the customer
"""

from __future__ import annotations

import base64
import dataclasses
import email.mime.text
import json
import os
import sys
import uuid
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from production.channels.kafka_producer import publish_ticket
from src.agent.models import Channel, TicketMessage

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

_seen_message_ids: set[str] = set()
_last_history_id: str | None = None

# Module-level singleton handler (used by webhooks endpoint)
_handler_instance: "GmailHandler | None" = None


def _get_handler() -> "GmailHandler":
    """Return (or create) the module-level GmailHandler singleton."""
    global _handler_instance
    if _handler_instance is None:
        _handler_instance = GmailHandler()
    return _handler_instance


# ---------------------------------------------------------------------------
# GmailHandler class
# ---------------------------------------------------------------------------


class GmailHandler:
    """Handles Gmail Pub/Sub push notifications and outbound reply sending."""

    def __init__(self) -> None:
        self.service: Any = None

    # ------------------------------------------------------------------
    # Credentials & service setup
    # ------------------------------------------------------------------

    async def setup_credentials(self) -> None:
        """Load Gmail API credentials from GMAIL_CREDENTIALS_JSON env var.

        Errors are logged to stderr; never raises.
        """
        try:
            creds_path = os.environ.get("GMAIL_CREDENTIALS_JSON")
            if not creds_path:
                raise KeyError("GMAIL_CREDENTIALS_JSON not set")

            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build

            creds = Credentials.from_authorized_user_file(
                creds_path,
                scopes=["https://www.googleapis.com/auth/gmail.modify"],
            )
            self.service = build("gmail", "v1", credentials=creds)
        except (FileNotFoundError, KeyError) as e:
            print(f"[gmail_handler] credentials error: {type(e).__name__}: {e}", file=sys.stderr)
            self.service = None
        except Exception as e:
            print(f"[gmail_handler] ERROR in setup_credentials: {type(e).__name__}: {e}", file=sys.stderr)
            self.service = None

    # ------------------------------------------------------------------
    # Watch inbox (register Pub/Sub push)
    # ------------------------------------------------------------------

    async def watch_inbox(self) -> dict:
        """Register Gmail inbox watch for Pub/Sub push notifications.

        Stores returned historyId in module-level _last_history_id.
        Returns the full API response dict, or {} on error.
        """
        global _last_history_id
        try:
            if self.service is None:
                print("[gmail_handler] WARNING: watch_inbox called with no service", file=sys.stderr)
                return {}
            project_id = os.environ.get("GOOGLE_CLOUD_PROJECT_ID", "")
            response = (
                self.service.users()
                .watches()
                .watch(
                    userId="me",
                    body={
                        "labelIds": ["INBOX"],
                        "topicName": f"projects/{project_id}/topics/gmail-notifications",
                    },
                )
                .execute()
            )
            _last_history_id = response.get("historyId")
            return response
        except Exception as e:
            print(f"[gmail_handler] ERROR in watch_inbox: {type(e).__name__}: {e}", file=sys.stderr)
            return {}

    # ------------------------------------------------------------------
    # Process Pub/Sub push notification
    # ------------------------------------------------------------------

    async def process_pub_sub_push(self, payload: dict) -> None:
        """Decode a Gmail Pub/Sub push payload and publish TicketMessages.

        Steps:
        1. Decode base64url data → extract historyId
        2. Idempotency gate: if historyId == _last_history_id → return (no-op)
        3. Call history.list(startHistoryId=_last_history_id)
        4. For each new message: fetch, normalise, publish
        5. Update _last_history_id
        """
        global _last_history_id, _seen_message_ids
        try:
            # Step 1: decode payload
            raw_data = payload["message"]["data"]
            # Pad base64 to multiple of 4
            padded = raw_data + "=="
            decoded_bytes = base64.urlsafe_b64decode(padded)
            notification = json.loads(decoded_bytes)
            history_id = str(notification.get("historyId", ""))

            # Step 2: idempotency gate
            if history_id == _last_history_id:
                return

            # Step 3: call history.list
            if self.service is None:
                print("[gmail_handler] WARNING: process_pub_sub_push called with no service", file=sys.stderr)
                _last_history_id = history_id
                return

            start_id = _last_history_id or history_id
            history_response = (
                self.service.users()
                .history()
                .list(userId="me", startHistoryId=start_id)
                .execute()
            )
            history_entries = history_response.get("history", [])

            # Step 4: process each new message
            for entry in history_entries:
                for msg_stub in entry.get("messages", entry.get("messagesAdded", [])):
                    # Support both formats: direct message stub or {message: {...}}
                    if "message" in msg_stub:
                        msg_id = msg_stub["message"]["id"]
                    else:
                        msg_id = msg_stub.get("id", "")

                    if not msg_id or msg_id in _seen_message_ids:
                        continue

                    ticket = await self._fetch_and_normalise(msg_id, history_id)
                    if ticket is not None:
                        try:
                            await publish_ticket(ticket)
                        except Exception as kafka_err:
                            print(f"[gmail_handler] Kafka publish error: {kafka_err}", file=sys.stderr)
                        _seen_message_ids.add(msg_id)

            # Step 5: update state
            _last_history_id = history_id

        except Exception as e:
            print(f"[gmail_handler] ERROR in process_pub_sub_push: {type(e).__name__}: {e}", file=sys.stderr)

    # ------------------------------------------------------------------
    # Fetch and normalise a single Gmail message
    # ------------------------------------------------------------------

    async def _fetch_and_normalise(self, msg_id: str, history_id: str) -> TicketMessage | None:
        """Fetch full message and return a TicketMessage, or None on error."""
        try:
            msg = (
                self.service.users()
                .messages()
                .get(userId="me", id=msg_id, format="full")
                .execute()
            )

            thread_id = msg.get("threadId", "")
            snippet = msg.get("snippet", "")
            payload_part = msg.get("payload", {})
            headers = payload_part.get("headers", [])

            # Extract headers
            from_header = next((h["value"] for h in headers if h["name"] == "From"), "")
            subject = next((h["value"] for h in headers if h["name"] == "Subject"), "(no subject)")

            # Parse email address from "Name <email@example.com>"
            customer_email = self._extract_email_address(from_header)
            customer_name = self._extract_display_name(from_header)

            # Extract body: text/plain preferred, fallback to snippet
            body = self._extract_body(payload_part, snippet)
            body = body[:4000]  # truncate to 4000 chars

            return TicketMessage(
                id=str(uuid.uuid4()),
                channel=Channel.EMAIL,
                customer_name=customer_name or customer_email or "Unknown",
                customer_email=customer_email,
                customer_phone=None,
                subject=subject,
                message=body,
                received_at=datetime.now(ZoneInfo("Asia/Karachi")).isoformat(),
                metadata={
                    "thread_id": thread_id,
                    "message_id": msg_id,
                    "subject": subject,
                    "gmail_history_id": history_id,
                },
            )
        except Exception as e:
            print(f"[gmail_handler] ERROR in _fetch_and_normalise: {type(e).__name__}: {e}", file=sys.stderr)
            return None

    # ------------------------------------------------------------------
    # Send reply
    # ------------------------------------------------------------------

    async def send_reply(self, thread_id: str, to_email: str, body: str) -> str:
        """Send a threaded Gmail reply.

        Returns the sent message ID, or empty string on error.
        """
        try:
            mime_msg = email.mime.text.MIMEText(body, "plain")
            mime_msg["To"] = to_email
            mime_msg["Subject"] = "Re: NexaFlow Support"

            raw = base64.urlsafe_b64encode(mime_msg.as_bytes()).decode()
            result = (
                self.service.users()
                .messages()
                .send(
                    userId="me",
                    body={"raw": raw, "threadId": thread_id},
                )
                .execute()
            )
            return result.get("id", "")
        except Exception as e:
            print(f"[gmail_handler] ERROR in send_reply: {type(e).__name__}: {e}", file=sys.stderr)
            return ""

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_email_address(from_header: str) -> str:
        """Parse 'Display Name <email@example.com>' → 'email@example.com'."""
        if "<" in from_header and ">" in from_header:
            return from_header.split("<")[1].rstrip(">").strip()
        return from_header.strip()

    @staticmethod
    def _extract_display_name(from_header: str) -> str:
        """Parse 'Display Name <email@example.com>' → 'Display Name'."""
        if "<" in from_header:
            return from_header.split("<")[0].strip().strip('"')
        return ""

    @staticmethod
    def _extract_body(payload_part: dict, snippet: str) -> str:
        """Extract plain text body from Gmail message payload.

        Tries text/plain MIME part first, falls back to snippet.
        """
        # Check if top-level part is text/plain
        mime_type = payload_part.get("mimeType", "")
        if mime_type == "text/plain":
            data = payload_part.get("body", {}).get("data", "")
            if data:
                try:
                    return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
                except Exception:
                    pass

        # Walk multipart
        for part in payload_part.get("parts", []):
            if part.get("mimeType") == "text/plain":
                data = part.get("body", {}).get("data", "")
                if data:
                    try:
                        return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
                    except Exception:
                        pass

        # Fallback to snippet
        return snippet
