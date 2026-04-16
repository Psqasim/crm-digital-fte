"""
production/api/web_form_routes.py
Phase 4C: Web form FastAPI router — submit, ticket lookup, metrics.
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from production.channels.web_form_handler import WebFormInput, submit_ticket
from production.database import queries
from production.database.queries import get_channel_metrics, get_db_pool

router = APIRouter()


# ---------------------------------------------------------------------------
# Dependency helper — lazily returns the shared pool
# ---------------------------------------------------------------------------


async def _pool():
    return await get_db_pool()


# ---------------------------------------------------------------------------
# POST /support/submit
# ---------------------------------------------------------------------------


@router.post("/support/submit")
async def submit_support_ticket(body: WebFormInput) -> JSONResponse:
    """Accept a web form submission, persist to DB, publish to Kafka.

    Returns 201 with ticket ID on success, 500 on DB failure, 422 on bad input.
    """
    pool = await _pool()
    result = await submit_ticket(pool, body)
    if result is None:
        return JSONResponse({"detail": "Internal server error"}, status_code=500)
    return JSONResponse(result, status_code=201)


# ---------------------------------------------------------------------------
# GET /support/ticket/{ticket_id}
# ---------------------------------------------------------------------------


@router.get("/support/ticket/{ticket_id}")
async def get_ticket(ticket_id: str) -> JSONResponse:
    """Return ticket details by display ID (TKT-XXXXXXXX) or raw UUID."""
    pool = await _pool()
    ticket = await queries.get_ticket_by_display_id(pool, ticket_id)
    if ticket is None:
        return JSONResponse({"detail": "Ticket not found"}, status_code=404)
    # Serialise datetime objects to ISO strings for JSON
    serialised = {
        k: v.isoformat() if hasattr(v, "isoformat") else v
        for k, v in ticket.items()
    }
    return JSONResponse(serialised, status_code=200)


# ---------------------------------------------------------------------------
# GET /support/tickets?email={email}
# ---------------------------------------------------------------------------


@router.get("/support/tickets")
async def get_tickets_by_email(
    email: str = Query(..., description="Customer email address"),
) -> JSONResponse:
    """Return all tickets submitted by a customer email address."""
    if not email or "@" not in email:
        return JSONResponse({"detail": "Valid email parameter required"}, status_code=400)
    pool = await _pool()
    tickets = await queries.get_tickets_by_email(pool, email)
    return JSONResponse(tickets, status_code=200, headers={"Cache-Control": "no-store"})


# ---------------------------------------------------------------------------
# GET /metrics/summary
# ---------------------------------------------------------------------------


@router.get("/metrics/summary")
async def get_metrics_summary() -> JSONResponse:
    """Return aggregated ticket metrics for the support dashboard."""
    pool = await _pool()
    metrics = await queries.get_metrics_summary(pool)
    # Serialise any datetime objects in recent_tickets
    for t in metrics.get("recent_tickets", []):
        for k, v in list(t.items()):
            if hasattr(v, "isoformat"):
                t[k] = v.isoformat()
    return JSONResponse(
        metrics,
        status_code=200,
        headers={"Cache-Control": "no-store"},
    )


# ---------------------------------------------------------------------------
# GET /metrics/channels
# ---------------------------------------------------------------------------


@router.get("/metrics/sentiment-report")
async def get_sentiment_report() -> JSONResponse:
    """Return today's sentiment analysis report (PKT timezone)."""
    pool = await _pool()
    data = await queries.get_sentiment_report(pool)
    return JSONResponse(data, status_code=200, headers={"Cache-Control": "no-store"})


@router.get("/metrics/channels")
async def get_metrics_channels() -> JSONResponse:
    """Return per-channel ticket metrics (email, whatsapp, web_form)."""
    pool = await _pool()
    data = await get_channel_metrics(pool)
    return JSONResponse(
        data,
        status_code=200,
        headers={"Cache-Control": "no-store"},
    )
