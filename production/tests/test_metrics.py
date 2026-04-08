"""
production/tests/test_metrics.py
Phase 4G: Tests for expanded metrics endpoints.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from production.api.main import app

_SUMMARY_PAYLOAD = {
    "total": 10,
    "open": 4,
    "in_progress": 2,
    "resolved": 3,
    "escalated": 1,
    "escalation_rate": 10.0,
    "escalation_rate_percent": 10.0,
    "avg_resolution_time_minutes": 35.5,
    "tickets_last_24h": 6,
    "top_categories": [
        {"category": "billing", "count": 5},
        {"category": "integration", "count": 3},
        {"category": "account", "count": 2},
    ],
    "channel_breakdown": {"email": 5, "whatsapp": 3, "web_form": 2},
    "channels": {"email": 5, "whatsapp": 3, "web_form": 2},
    "recent_tickets": [],
}

_CHANNELS_PAYLOAD = {
    "email": {"total": 5, "open": 2, "resolved": 3, "avg_resolution_min": 42.0},
    "whatsapp": {"total": 3, "open": 1, "resolved": 2, "avg_resolution_min": 28.5},
    "web_form": {"total": 2, "open": 1, "resolved": 1, "avg_resolution_min": 15.0},
}


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# GET /metrics/summary — expanded fields
# ---------------------------------------------------------------------------


@patch("production.api.web_form_routes.get_db_pool")
@patch("production.database.queries.get_metrics_summary", new_callable=AsyncMock)
def test_metrics_summary_expanded_fields(mock_summary, mock_pool, client):
    """GET /metrics/summary returns new Phase 4G fields."""
    mock_pool.return_value = MagicMock()
    mock_summary.return_value = _SUMMARY_PAYLOAD

    with patch("production.api.web_form_routes.queries.get_metrics_summary", mock_summary):
        resp = client.get("/metrics/summary")

    assert resp.status_code == 200
    data = resp.json()

    assert "escalation_rate_percent" in data
    assert "avg_resolution_time_minutes" in data
    assert "tickets_last_24h" in data
    assert "top_categories" in data
    assert "channel_breakdown" in data


# ---------------------------------------------------------------------------
# GET /metrics/channels — shape
# ---------------------------------------------------------------------------


@patch("production.api.web_form_routes.get_db_pool")
@patch("production.api.web_form_routes.get_channel_metrics", new_callable=AsyncMock)
def test_metrics_channels_shape(mock_channel_metrics, mock_pool, client):
    """GET /metrics/channels returns per-channel dict with required keys."""
    mock_pool.return_value = MagicMock()
    mock_channel_metrics.return_value = _CHANNELS_PAYLOAD

    resp = client.get("/metrics/channels")

    assert resp.status_code == 200
    data = resp.json()

    for channel in ("email", "whatsapp", "web_form"):
        assert channel in data, f"missing channel: {channel}"
        ch = data[channel]
        for field in ("total", "open", "resolved", "avg_resolution_min"):
            assert field in ch, f"missing field '{field}' in channel '{channel}'"


# ---------------------------------------------------------------------------
# GET /metrics/channels — values
# ---------------------------------------------------------------------------


@patch("production.api.web_form_routes.get_db_pool")
@patch("production.api.web_form_routes.get_channel_metrics", new_callable=AsyncMock)
def test_metrics_channels_values(mock_channel_metrics, mock_pool, client):
    """GET /metrics/channels returns correct numeric values."""
    mock_pool.return_value = MagicMock()
    mock_channel_metrics.return_value = _CHANNELS_PAYLOAD

    resp = client.get("/metrics/channels")

    assert resp.status_code == 200
    data = resp.json()

    assert data["email"]["total"] == 5
    assert data["whatsapp"]["resolved"] == 2
    assert data["web_form"]["avg_resolution_min"] == 15.0
