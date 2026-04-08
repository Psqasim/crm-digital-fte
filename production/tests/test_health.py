"""
production/tests/test_health.py
Phase 4D: Tests for GET /health endpoint.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from production.api.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Healthy — DB responds
# ---------------------------------------------------------------------------


@patch("production.api.main.get_db_pool")
def test_health_healthy(mock_get_pool, client):
    """GET /health returns 200 with status=healthy when DB is up."""
    mock_conn = AsyncMock()
    mock_conn.fetchval = AsyncMock(return_value=1)

    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    mock_pool = MagicMock()
    mock_pool.acquire.return_value = mock_ctx
    mock_get_pool.return_value = mock_pool

    resp = client.get("/health")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["version"] == "1.0.0"
    assert data["database"] == "connected"
    assert "timestamp" in data
    assert "PKT" in data["timestamp"]


# ---------------------------------------------------------------------------
# Degraded — DB unreachable
# ---------------------------------------------------------------------------


@patch("production.api.main.get_db_pool")
def test_health_degraded(mock_get_pool, client):
    """GET /health returns 200 with status=degraded when DB is unreachable."""
    mock_get_pool.side_effect = Exception("connection refused")

    resp = client.get("/health")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "degraded"
    assert data["database"] == "disconnected"
    assert data["version"] == "1.0.0"


# ---------------------------------------------------------------------------
# Shape validation
# ---------------------------------------------------------------------------


@patch("production.api.main.get_db_pool")
def test_health_response_shape(mock_get_pool, client):
    """GET /health always returns all four required keys."""
    mock_get_pool.side_effect = RuntimeError("DB down")

    resp = client.get("/health")

    data = resp.json()
    for key in ("status", "version", "database", "timestamp"):
        assert key in data, f"missing key: {key}"
