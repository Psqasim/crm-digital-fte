"""
production/api/main.py
Phase 4D: FastAPI application entry-point.

Registers all routers, wires lifespan (DB pool init + Kafka shutdown),
and adds CORS middleware.
"""

from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()

import asyncio
import json
import logging
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from production.api.agent_routes import router as agent_router
from production.api.chat_routes import router as chat_router
from production.api.web_form_routes import router as web_form_router
from production.api.webhooks import router as webhooks_router
from production.channels.kafka_producer import stop_kafka_producer
from production.database.queries import get_db_pool

logger = logging.getLogger(__name__)

_PKT = ZoneInfo("Asia/Karachi")


# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown
# ---------------------------------------------------------------------------


async def _ticket_processor_loop() -> None:
    """Background task: process pending tickets every 30 seconds.

    Runs inside the FastAPI process so HF Spaces (single container) can
    resolve tickets without a separate worker pod.
    """
    from production.api.agent_routes import _process_ticket_background  # noqa: PLC0415
    from production.database.queries import get_pending_tickets  # noqa: PLC0415

    await asyncio.sleep(10)  # wait for DB pool to be ready
    while True:
        try:
            pool = await get_db_pool()
            tickets = await get_pending_tickets(pool)
            if tickets:
                logger.info("[worker] processing %d pending tickets", len(tickets))
                for t in tickets:
                    asyncio.create_task(_process_ticket_background(t["ticket_id"]))
            else:
                logger.debug("[worker] no pending tickets")
        except Exception:
            logger.exception("[worker] poll error — retrying in 30s")
        await asyncio.sleep(30)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise DB pool on startup; start background worker; close on shutdown."""
    try:
        app.state.db_pool = await get_db_pool()
        logger.info("[lifespan] DB pool ready")
    except Exception:
        logger.exception("[lifespan] DB pool init failed — continuing without pool")
        app.state.db_pool = None

    # Start background ticket processor (replaces separate worker process on HF Spaces)
    worker_task = asyncio.create_task(_ticket_processor_loop())
    logger.info("[lifespan] background ticket processor started")

    # Set up Gmail credentials and register Pub/Sub watch
    try:
        from production.channels.gmail_handler import _get_handler as _get_gmail_handler  # noqa: PLC0415
        gmail = _get_gmail_handler()
        await gmail.setup_credentials()
        if gmail.service is not None:
            await gmail.watch_inbox()
            logger.info("[lifespan] Gmail watch registered")
        else:
            logger.warning("[lifespan] Gmail credentials not set — email channel disabled")
    except Exception:
        logger.exception("[lifespan] Gmail setup failed — continuing without email channel")

    yield

    worker_task.cancel()
    await stop_kafka_producer()
    logger.info("[lifespan] shutdown complete")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="NexaFlow Customer Success FTE",
    version="1.0.0",
    description="AI-powered customer support for NexaFlow B2B SaaS",
    lifespan=lifespan,
)

# CORS — allow Next.js dev server and production origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://nexaflow.com",
        "https://crm-digital-fte-two.vercel.app",
        "https://*.vercel.app",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Structured request logging middleware (JSON → stderr)
# ---------------------------------------------------------------------------


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log every HTTP request as a JSON line to stderr."""
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 1)
    ts = datetime.now(_PKT).isoformat()
    record = {
        "ts": ts,
        "method": request.method,
        "path": request.url.path,
        "status": response.status_code,
        "duration_ms": duration_ms,
    }
    print(json.dumps(record), file=sys.stderr)
    return response

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(webhooks_router)          # /webhooks/gmail, /webhooks/whatsapp
app.include_router(web_form_router)          # /support/submit, /support/ticket/{id}, /metrics/summary
app.include_router(agent_router)             # /agent/process/{id}, /agent/process-pending
app.include_router(chat_router)              # /chat/message


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------


@app.get("/health")
async def health_check() -> JSONResponse:
    """Return service health status including DB connectivity.

    Returns 200 with status="healthy" when DB is up,
    or status="degraded" when DB is unreachable (never 500).
    """
    timestamp = datetime.now(ZoneInfo("Asia/Karachi")).strftime(
        "%A, %B %d, %Y at %I:%M %p PKT"
    )

    db_status = "connected"
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
    except Exception:
        logger.exception("[health] DB check failed")
        db_status = "disconnected"

    status = "healthy" if db_status == "connected" else "degraded"

    return JSONResponse(
        {
            "status": status,
            "version": "1.0.0",
            "database": db_status,
            "timestamp": timestamp,
        },
        status_code=200,
    )
