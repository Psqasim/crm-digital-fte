"""
production/workers/message_processor.py
Phase 4D: Standalone worker that polls /agent/process-pending every 30 seconds.

Run with:
    python -m production.workers.message_processor
or via PM2:
    pm2 start "python -m production.workers.message_processor" --name crm-worker

The worker does NOT import FastAPI — it makes HTTP calls to the running API server
so the agent processing runs inside the server's event loop (DB pool, CORS, etc.).
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [worker] %(levelname)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# Base URL of the FastAPI server; override via API_BASE_URL env var
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
POLL_INTERVAL_SECONDS = int(os.environ.get("WORKER_POLL_INTERVAL", "30"))


async def poll_once(client: httpx.AsyncClient) -> None:
    """Call /agent/process-pending once and log the result."""
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
    except httpx.ConnectError as e:
        logger.warning("Connection error — will retry next cycle: %s", e)
    except httpx.TimeoutException as e:
        logger.warning("Timeout — will retry next cycle: %s", e)
    except Exception:
        logger.exception("Unexpected error in poll_once")


async def run_worker() -> None:
    """Main loop: poll every POLL_INTERVAL_SECONDS until interrupted."""
    logger.info(
        "Worker started — polling %s every %ds",
        API_BASE_URL,
        POLL_INTERVAL_SECONDS,
    )
    async with httpx.AsyncClient() as client:
        while True:
            await poll_once(client)
            await asyncio.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
