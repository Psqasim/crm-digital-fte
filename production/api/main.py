"""
production/api/main.py
Phase 4D: FastAPI application entry-point.

Registers all routers, wires lifespan (DB pool init + Kafka shutdown),
and adds CORS middleware.
"""

from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from production.api.agent_routes import router as agent_router
from production.api.web_form_routes import router as web_form_router
from production.api.webhooks import router as webhooks_router
from production.channels.kafka_producer import stop_kafka_producer
from production.database.queries import get_db_pool

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise DB pool on startup; close Kafka producer on shutdown."""
    try:
        app.state.db_pool = await get_db_pool()
        logger.info("[lifespan] DB pool ready")
    except Exception:
        logger.exception("[lifespan] DB pool init failed — continuing without pool")
        app.state.db_pool = None

    yield

    await stop_kafka_producer()
    logger.info("[lifespan] Kafka producer stopped")


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
    allow_origins=["http://localhost:3000", "https://nexaflow.com"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(webhooks_router)          # /webhooks/gmail, /webhooks/whatsapp
app.include_router(web_form_router)          # /support/submit, /support/ticket/{id}, /metrics/summary
app.include_router(agent_router)             # /agent/process/{id}, /agent/process-pending


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
