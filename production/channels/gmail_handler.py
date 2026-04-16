"""
production/channels/gmail_handler.py
Phase 4C + 7E: Gmail channel handler — Pub/Sub push → DB → AI agent → reply.

Flow:
  1. Gmail Pub/Sub push notification → /webhooks/gmail
  2. process_pub_sub_push() decodes historyId, deduplicates via DB
  3. For each new message: fetch full content → write to DB → run AI agent
  4. send_reply() sends a threaded Gmail reply back to the customer
"""

from __future__ import annotations

import base64
import email.mime.text
import json
import os
import sys
import uuid
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

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
        """Load Gmail API credentials from GMAIL_CREDENTIALS_JSON_CONTENT env var.

        Reads JSON content directly from env var (no file needed on HF Spaces).
        Falls back to GMAIL_CREDENTIALS_JSON file path if content var not set.
        """
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build

            scopes = ["https://www.googleapis.com/auth/gmail.modify"]

            # Prefer JSON content from env var (HF Spaces secrets)
            creds_content = os.environ.get("GMAIL_CREDENTIALS_JSON_CONTENT", "").strip()
            if creds_content:
                creds_dict = json.loads(creds_content)
                creds = Credentials.from_authorized_user_info(creds_dict, scopes=scopes)
            else:
                # Fallback: file path (local dev)
                creds_path = os.environ.get("GMAIL_CREDENTIALS_JSON")
                if not creds_path:
                    raise KeyError("Neither GMAIL_CREDENTIALS_JSON_CONTENT nor GMAIL_CREDENTIALS_JSON is set")
                creds = Credentials.from_authorized_user_file(creds_path, scopes=scopes)

            self.service = build("gmail", "v1", credentials=creds)
            print("[gmail_handler] credentials loaded OK", file=sys.stderr)
        except Exception as e:
            print(f"[gmail_handler] ERROR in setup_credentials: {type(e).__name__}: {e}", file=sys.stderr)
            self.service = None

    # ------------------------------------------------------------------
    # Watch inbox (register Pub/Sub push)
    # ------------------------------------------------------------------

    async def watch_inbox(self) -> dict:
        """Register Gmail inbox watch for Pub/Sub push notifications.

        Must be called on startup and renewed every 7 days.
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
            print(f"[gmail_handler] watch registered, historyId={_last_history_id}", file=sys.stderr)
            return response
        except Exception as e:
            print(f"[gmail_handler] ERROR in watch_inbox: {type(e).__name__}: {e}", file=sys.stderr)
            return {}

    # ------------------------------------------------------------------
    # Process Pub/Sub push notification
    # ------------------------------------------------------------------

    async def process_pub_sub_push(self, payload: dict) -> None:
        """Decode a Gmail Pub/Sub push payload, write to DB, run AI agent.

        Steps:
        1. Decode base64url data → extract historyId
        2. Call history.list to find new messages
        3. For each new message: fetch → write to DB → run agent → reply
        """
        global _last_history_id
        try:
            # Step 1: decode payload
            raw_data = payload["message"]["data"]
            padded = raw_data + "=="
            decoded_bytes = base64.urlsafe_b64decode(padded)
            notification = json.loads(decoded_bytes)
            history_id = str(notification.get("historyId", ""))

            if not history_id:
                return

            if self.service is None:
                print("[gmail_handler] WARNING: no service — skipping", file=sys.stderr)
                _last_history_id = history_id
                return

            # Step 2: fetch history since last known ID
            start_id = _last_history_id or history_id
            history_response = (
                self.service.users()
                .history()
                .list(userId="me", startHistoryId=start_id, historyTypes=["messageAdded"])
                .execute()
            )
            history_entries = history_response.get("history", [])

            # Step 3: process each new message
            from production.database.queries import get_db_pool  # noqa: PLC0415
            from production.database import queries  # noqa: PLC0415

            pool = await get_db_pool()

            for entry in history_entries:
                for msg_stub in entry.get("messagesAdded", []):
                    msg_id = msg_stub.get("message", {}).get("id", "")
                    if not msg_id:
                        continue

                    # DB-level dedup
                    claimed = await queries.claim_gmail_message(pool, msg_id)
                    if not claimed:
                        print(f"[gmail_handler] duplicate msg_id {msg_id} — skipping", file=sys.stderr)
                        continue

                    await self._process_single_message(pool, queries, msg_id)

            _last_history_id = history_id

        except Exception as e:
            print(f"[gmail_handler] ERROR in process_pub_sub_push: {type(e).__name__}: {e}", file=sys.stderr)

    async def _process_single_message(self, pool, queries, msg_id: str) -> None:
        """Fetch one Gmail message, create DB records, run agent, send reply."""
        try:
            msg = (
                self.service.users()
                .messages()
                .get(userId="me", id=msg_id, format="full")
                .execute()
            )

            thread_id = msg.get("threadId", "")
            payload_part = msg.get("payload", {})
            headers = payload_part.get("headers", [])

            from_header = next((h["value"] for h in headers if h["name"] == "From"), "")
            subject = next((h["value"] for h in headers if h["name"] == "Subject"), "(no subject)")

            customer_email = self._extract_email_address(from_header)
            customer_name = self._extract_display_name(from_header) or customer_email or "Customer"
            body = self._extract_body(payload_part, msg.get("snippet", ""))[:4000]

            # Skip emails from ourselves (avoid reply loops)
            my_email = os.environ.get("GMAIL_USER_EMAIL", "").strip().lower()
            if customer_email.lower() == my_email:
                print(f"[gmail_handler] skipping own email from {customer_email}", file=sys.stderr)
                return

            # Write to DB
            customer = await queries.get_or_create_customer(pool, customer_email, name=customer_name)
            if customer is None:
                print("[gmail_handler] ERROR: could not get/create customer", file=sys.stderr)
                return
            customer_id = str(customer["id"])

            conversation_id = await queries.create_conversation(pool, customer_id, "email")
            if not conversation_id:
                print("[gmail_handler] ERROR: could not create conversation", file=sys.stderr)
                return

            await queries.add_message(pool, conversation_id, role="customer", content=body, channel="email")

            internal_ticket_id = await queries.create_ticket(
                pool, conversation_id, customer_id,
                channel="email", subject=subject[:100],
            )
            if not internal_ticket_id:
                print("[gmail_handler] ERROR: could not create ticket", file=sys.stderr)
                return

            # Reload ticket for agent
            ticket = await queries.get_ticket_by_display_id(pool, internal_ticket_id)
            if not ticket:
                return

            # Run AI agent
            from production.api.agent_routes import _run_agent_on_ticket  # noqa: PLC0415
            agent_resp = await _run_agent_on_ticket(pool, ticket)

            # Send Gmail reply
            if agent_resp and agent_resp.response_text:
                await self.send_reply(thread_id, customer_email, agent_resp.response_text)
                print(
                    f"[gmail_handler] replied to {customer_email} for ticket {ticket['ticket_id']}",
                    file=sys.stderr,
                )

        except Exception as e:
            print(f"[gmail_handler] ERROR in _process_single_message: {type(e).__name__}: {e}", file=sys.stderr)

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
        if "<" in from_header and ">" in from_header:
            return from_header.split("<")[1].rstrip(">").strip()
        return from_header.strip()

    @staticmethod
    def _extract_display_name(from_header: str) -> str:
        if "<" in from_header:
            return from_header.split("<")[0].strip().strip('"')
        return ""

    @staticmethod
    def _extract_body(payload_part: dict, snippet: str) -> str:
        mime_type = payload_part.get("mimeType", "")
        if mime_type == "text/plain":
            data = payload_part.get("body", {}).get("data", "")
            if data:
                try:
                    return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
                except Exception:
                    pass

        for part in payload_part.get("parts", []):
            if part.get("mimeType") == "text/plain":
                data = part.get("body", {}).get("data", "")
                if data:
                    try:
                        return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
                    except Exception:
                        pass

        return snippet
