"""
production/workers/message_processor.py
Phase 4E: Primary = Kafka consumer; fallback = httpx polling every 30 s.

- If KAFKA_BOOTSTRAP_SERVERS is set, runs the Confluent Cloud consumer loop.
- Otherwise falls back to the original Phase-4D httpx polling loop so the
  system still works in environments without Kafka credentials.

Run with:
    python -m production.workers.message_processor
or via PM2:
    pm2 start "python -m production.workers.message_processor" --name crm-worker
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [worker] %(levelname)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Kafka primary path
# ---------------------------------------------------------------------------

def _run_kafka() -> None:
    """Start the Confluent Cloud consumer (blocking)."""
    logger.info("KAFKA_BOOTSTRAP_SERVERS detected — starting Kafka consumer")
    from production.kafka.consumer import run_consumer  # noqa: PLC0415
    run_consumer()


# ---------------------------------------------------------------------------
# httpx polling fallback
# ---------------------------------------------------------------------------

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
POLL_INTERVAL_SECONDS = int(os.environ.get("WORKER_POLL_INTERVAL", "30"))


async def _poll_once(client) -> None:
    import httpx  # noqa: PLC0415
    try:
        response = await client.post(
            f"{API_BASE_URL}/agent/process-pending",
            timeout=15.0,
        )
        if response.status_code == 200:
            data = response.json()
            queued = data.get("queued", 0)
            ticket_ids = data.get("ticket_ids", [])
            if queued > 0:
                logger.info("Processing %d pending ticket(s): %s", queued, ticket_ids)
            else:
                logger.debug("No pending tickets found")
        else:
            logger.warning(
                "Unexpected status from /agent/process-pending: %d — %s",
                response.status_code,
                response.text[:200],
            )
    except Exception:
        logger.exception("Unexpected error in poll_once")


async def _run_polling_loop() -> None:
    import httpx  # noqa: PLC0415
    logger.info(
        "No Kafka config — falling back to httpx polling %s every %ds",
        API_BASE_URL,
        POLL_INTERVAL_SECONDS,
    )
    async with httpx.AsyncClient() as client:
        while True:
            await _poll_once(client)
            await asyncio.sleep(POLL_INTERVAL_SECONDS)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if os.environ.get("KAFKA_BOOTSTRAP_SERVERS"):
        try:
            _run_kafka()
        except KeyboardInterrupt:
            logger.info("Kafka consumer stopped by user")
    else:
        try:
            asyncio.run(_run_polling_loop())
        except KeyboardInterrupt:
            logger.info("Polling worker stopped by user")
