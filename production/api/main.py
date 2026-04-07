"""
production/api/main.py
Phase 4C: FastAPI application entry-point.

Registers webhook routes and wires Kafka producer shutdown on app lifespan.
"""

from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()

from contextlib import asynccontextmanager

from fastapi import FastAPI

from production.api.web_form_routes import router as web_form_router
from production.api.webhooks import router
from production.channels.kafka_producer import stop_kafka_producer


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: yield → handle requests → shutdown Kafka producer."""
    yield
    await stop_kafka_producer()


app = FastAPI(lifespan=lifespan, title="CRM Digital FTE — Channel Webhooks")
app.include_router(router)
app.include_router(web_form_router)
