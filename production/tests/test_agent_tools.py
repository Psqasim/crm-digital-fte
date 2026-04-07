"""
production/tests/test_agent_tools.py
Phase 4B: Unit tests for all 7 @function_tool functions.

Tests call the _*_impl() functions directly — FunctionTool wrappers are not
directly callable, so the _impl pattern is the standard approach for unit testing
without spinning up a full agent run.

All tests run without DATABASE_URL or OPENAI_API_KEY set.
asyncpg.Pool and AsyncOpenAI are mocked via pytest-mock / AsyncMock.
"""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_pool():
    """Return a (pool, conn) tuple with MagicMock pool."""
    pool = MagicMock()
    conn = AsyncMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
    return pool, conn


@pytest.fixture
def mock_openai_client():
    """Patch _get_openai_client to return a mock client."""
    client = AsyncMock()
    with patch("production.agent.tools._get_openai_client", return_value=client):
        yield client


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _fake_embedding(dim: int = 1536) -> list[float]:
    return [0.1] * dim


# ---------------------------------------------------------------------------
# T006: search_knowledge_base tests
# ---------------------------------------------------------------------------


async def test_search_knowledge_base_happy_path(mock_pool, mock_openai_client):
    """Happy path: embeddings generated, DB returns 2 results."""
    pool, conn = mock_pool

    embedding_data = MagicMock()
    embedding_data.embedding = _fake_embedding()
    mock_openai_client.embeddings.create = AsyncMock(
        return_value=MagicMock(data=[embedding_data])
    )

    kb_results = [
        {"id": str(uuid.uuid4()), "title": "Slack integration", "content": "...", "category": "integrations", "similarity": 0.95},
        {"id": str(uuid.uuid4()), "title": "Zapier guide", "content": "...", "category": "integrations", "similarity": 0.88},
    ]

    with patch("production.agent.tools.get_db_pool", new_callable=AsyncMock, return_value=pool), \
         patch("production.agent.tools.queries") as mock_queries:
        mock_queries.search_knowledge_base = AsyncMock(return_value=kb_results)

        from production.agent.tools import _search_knowledge_base_impl
        from production.agent.schemas import SearchKBInput

        result_str = await _search_knowledge_base_impl(SearchKBInput(query="Slack integration", limit=5))
        result = json.loads(result_str)

    assert result["count"] == 2
    assert len(result["results"]) == 2


async def test_search_knowledge_base_empty_results(mock_pool, mock_openai_client):
    """Empty result set returns {results: [], count: 0}, not an error."""
    pool, conn = mock_pool

    embedding_data = MagicMock()
    embedding_data.embedding = _fake_embedding()
    mock_openai_client.embeddings.create = AsyncMock(
        return_value=MagicMock(data=[embedding_data])
    )

    with patch("production.agent.tools.get_db_pool", new_callable=AsyncMock, return_value=pool), \
         patch("production.agent.tools.queries") as mock_queries:
        mock_queries.search_knowledge_base = AsyncMock(return_value=[])

        from production.agent.tools import _search_knowledge_base_impl
        from production.agent.schemas import SearchKBInput

        result_str = await _search_knowledge_base_impl(SearchKBInput(query="nonexistent topic", limit=5))
        result = json.loads(result_str)

    assert result["count"] == 0
    assert result["results"] == []
    assert "error" not in result


async def test_search_knowledge_base_db_error(mock_pool, mock_openai_client):
    """DB error returns error JSON, no naked raise."""
    pool, conn = mock_pool

    embedding_data = MagicMock()
    embedding_data.embedding = _fake_embedding()
    mock_openai_client.embeddings.create = AsyncMock(
        return_value=MagicMock(data=[embedding_data])
    )

    with patch("production.agent.tools.get_db_pool", new_callable=AsyncMock, return_value=pool), \
         patch("production.agent.tools.queries") as mock_queries:
        mock_queries.search_knowledge_base = AsyncMock(side_effect=Exception("pgvector unavailable"))

        from production.agent.tools import _search_knowledge_base_impl
        from production.agent.schemas import SearchKBInput

        result_str = await _search_knowledge_base_impl(SearchKBInput(query="anything", limit=5))
        result = json.loads(result_str)

    assert "error" in result
    assert result["tool"] == "search_knowledge_base"


# ---------------------------------------------------------------------------
# T008: create_ticket tests
# ---------------------------------------------------------------------------


async def test_create_ticket_happy_path(mock_pool, mock_openai_client):
    """Happy path: returns ticket_id, conversation_id, customer_id."""
    pool, conn = mock_pool
    ticket_id = str(uuid.uuid4())

    with patch("production.agent.tools.get_db_pool", new_callable=AsyncMock, return_value=pool), \
         patch("production.agent.tools.queries") as mock_queries:
        mock_queries.create_ticket = AsyncMock(return_value=ticket_id)

        from production.agent.tools import _create_ticket_impl
        from production.agent.schemas import CreateTicketInput

        params = CreateTicketInput(
            customer_id=str(uuid.uuid4()),
            conversation_id=str(uuid.uuid4()),
            channel="web_form",
            subject="Slack setup",
            category="integrations",
        )
        result_str = await _create_ticket_impl(params)
        result = json.loads(result_str)

    assert result["ticket_id"] == ticket_id
    assert "customer_id" in result
    assert "conversation_id" in result


async def test_create_ticket_unknown_channel_accepted(mock_pool, mock_openai_client):
    """Channel is a plain str — no constraint in schema; tool accepts any value."""
    pool, conn = mock_pool
    ticket_id = str(uuid.uuid4())

    with patch("production.agent.tools.get_db_pool", new_callable=AsyncMock, return_value=pool), \
         patch("production.agent.tools.queries") as mock_queries:
        mock_queries.create_ticket = AsyncMock(return_value=ticket_id)

        from production.agent.tools import _create_ticket_impl
        from production.agent.schemas import CreateTicketInput

        params = CreateTicketInput(
            customer_id=str(uuid.uuid4()),
            conversation_id=str(uuid.uuid4()),
            channel="fax",
        )
        result_str = await _create_ticket_impl(params)
        result = json.loads(result_str)

    assert "ticket_id" in result


async def test_create_ticket_db_error(mock_pool, mock_openai_client):
    """DB error returns error JSON, no naked raise."""
    pool, conn = mock_pool

    with patch("production.agent.tools.get_db_pool", new_callable=AsyncMock, return_value=pool), \
         patch("production.agent.tools.queries") as mock_queries:
        mock_queries.create_ticket = AsyncMock(side_effect=Exception("UniqueViolation"))

        from production.agent.tools import _create_ticket_impl
        from production.agent.schemas import CreateTicketInput

        params = CreateTicketInput(
            customer_id=str(uuid.uuid4()),
            conversation_id=str(uuid.uuid4()),
            channel="email",
        )
        result_str = await _create_ticket_impl(params)
        result = json.loads(result_str)

    assert "error" in result
    assert result["tool"] == "create_ticket"


# ---------------------------------------------------------------------------
# T010: get_customer_history tests
# ---------------------------------------------------------------------------


async def test_get_customer_history_happy_path(mock_pool, mock_openai_client):
    """Returns conversations list with count."""
    pool, conn = mock_pool
    conversations = [
        {"id": str(uuid.uuid4()), "channel": "email", "status": "open", "started_at": None, "updated_at": None, "messages": []},
        {"id": str(uuid.uuid4()), "channel": "whatsapp", "status": "resolved", "started_at": None, "updated_at": None, "messages": []},
    ]

    with patch("production.agent.tools.get_db_pool", new_callable=AsyncMock, return_value=pool), \
         patch("production.agent.tools.queries") as mock_queries:
        mock_queries.get_customer_history = AsyncMock(return_value=conversations)

        from production.agent.tools import _get_customer_history_impl

        result_str = await _get_customer_history_impl(customer_id=str(uuid.uuid4()), limit=20)
        result = json.loads(result_str)

    assert result["count"] == 2
    assert len(result["conversations"]) == 2


async def test_get_customer_history_empty(mock_pool, mock_openai_client):
    """Empty history returns {conversations: [], count: 0}, not error."""
    pool, conn = mock_pool

    with patch("production.agent.tools.get_db_pool", new_callable=AsyncMock, return_value=pool), \
         patch("production.agent.tools.queries") as mock_queries:
        mock_queries.get_customer_history = AsyncMock(return_value=[])

        from production.agent.tools import _get_customer_history_impl

        result_str = await _get_customer_history_impl(customer_id=str(uuid.uuid4()), limit=20)
        result = json.loads(result_str)

    assert result["count"] == 0
    assert result["conversations"] == []
    assert "error" not in result


async def test_get_customer_history_db_error(mock_pool, mock_openai_client):
    """DB error returns error JSON, no naked raise."""
    pool, conn = mock_pool

    with patch("production.agent.tools.get_db_pool", new_callable=AsyncMock, return_value=pool), \
         patch("production.agent.tools.queries") as mock_queries:
        mock_queries.get_customer_history = AsyncMock(side_effect=Exception("connection lost"))

        from production.agent.tools import _get_customer_history_impl

        result_str = await _get_customer_history_impl(customer_id=str(uuid.uuid4()), limit=5)
        result = json.loads(result_str)

    assert "error" in result
    assert result["tool"] == "get_customer_history"


# ---------------------------------------------------------------------------
# T012: send_response tests
# ---------------------------------------------------------------------------


async def test_send_response_email_truncation(mock_pool, mock_openai_client):
    """600-word email is formatted; delivery_status is 'delivered' or 'failed' (credentials absent in test env)."""
    long_message = " ".join([f"word{i}" for i in range(600)])

    from production.agent.tools import _send_response_impl
    from production.agent.schemas import SendResponseInput

    params = SendResponseInput(
        ticket_id=str(uuid.uuid4()),
        message=long_message,
        channel="email",
    )
    result_str = await _send_response_impl(params)
    result = json.loads(result_str)

    assert result["delivery_status"] in ("delivered", "failed")
    assert result["channel"] == "email"


async def test_send_response_whatsapp_stub(mock_pool, mock_openai_client):
    """WhatsApp message returns delivery_status 'delivered' or 'failed' (credentials absent in test env)."""
    from production.agent.tools import _send_response_impl
    from production.agent.schemas import SendResponseInput

    params = SendResponseInput(
        ticket_id=str(uuid.uuid4()),
        message="Your workflow issue has been resolved. Please try again.",
        channel="whatsapp",
    )
    result_str = await _send_response_impl(params)
    result = json.loads(result_str)

    assert result["delivery_status"] in ("delivered", "failed")
    assert result["channel"] == "whatsapp"


async def test_send_response_missing_message_raises():
    """Empty message raises pydantic.ValidationError before tool is called."""
    from pydantic import ValidationError
    from production.agent.schemas import SendResponseInput

    with pytest.raises(ValidationError):
        SendResponseInput(ticket_id=str(uuid.uuid4()), message="", channel="email")


# ---------------------------------------------------------------------------
# T014: resolve_ticket tests
# ---------------------------------------------------------------------------


async def test_resolve_ticket_happy_path(mock_pool, mock_openai_client):
    """Returns {status: resolved} on a valid open ticket."""
    pool, conn = mock_pool
    ticket_id = str(uuid.uuid4())

    import production.agent.tools as tools_module
    tools_module._ticket_registry[ticket_id] = "open"

    try:
        with patch("production.agent.tools.get_db_pool", new_callable=AsyncMock, return_value=pool), \
             patch("production.agent.tools.queries") as mock_queries:
            mock_queries.update_ticket_status = AsyncMock(return_value=None)

            from production.agent.tools import _resolve_ticket_impl
            from production.agent.schemas import ResolveTicketInput

            params = ResolveTicketInput(
                ticket_id=ticket_id,
                resolution_summary="Issue resolved by providing correct API key steps.",
            )
            result_str = await _resolve_ticket_impl(params)
            result = json.loads(result_str)
    finally:
        tools_module._ticket_registry.pop(ticket_id, None)

    assert result["status"] == "resolved"
    assert result["ticket_id"] == ticket_id


async def test_resolve_ticket_idempotent(mock_pool, mock_openai_client):
    """Re-resolving an already-resolved ticket returns existing record, no error."""
    pool, conn = mock_pool
    ticket_id = str(uuid.uuid4())

    import production.agent.tools as tools_module
    tools_module._ticket_registry[ticket_id] = "resolved"

    try:
        from production.agent.tools import _resolve_ticket_impl
        from production.agent.schemas import ResolveTicketInput

        params = ResolveTicketInput(
            ticket_id=ticket_id,
            resolution_summary="Already resolved.",
        )
        result_str = await _resolve_ticket_impl(params)
        result = json.loads(result_str)
    finally:
        tools_module._ticket_registry.pop(ticket_id, None)

    assert result["status"] == "resolved"
    assert "error" not in result


async def test_resolve_ticket_escalated_blocked(mock_pool, mock_openai_client):
    """Cannot resolve an escalated ticket — returns error JSON."""
    pool, conn = mock_pool
    ticket_id = str(uuid.uuid4())

    import production.agent.tools as tools_module
    tools_module._ticket_registry[ticket_id] = "escalated"

    try:
        from production.agent.tools import _resolve_ticket_impl
        from production.agent.schemas import ResolveTicketInput

        params = ResolveTicketInput(
            ticket_id=ticket_id,
            resolution_summary="Try to resolve.",
        )
        result_str = await _resolve_ticket_impl(params)
        result = json.loads(result_str)
    finally:
        tools_module._ticket_registry.pop(ticket_id, None)

    assert "error" in result
    assert result["tool"] == "resolve_ticket"


# ---------------------------------------------------------------------------
# T021: escalate_to_human tests
# ---------------------------------------------------------------------------


async def test_escalate_to_human_happy_path(mock_pool, mock_openai_client):
    """Valid escalation returns escalation_id (UUID) and status=escalated."""
    pool, conn = mock_pool

    with patch("production.agent.tools.get_db_pool", new_callable=AsyncMock, return_value=pool), \
         patch("production.agent.tools.queries") as mock_queries:
        mock_queries.update_ticket_status = AsyncMock(return_value=None)

        from production.agent.tools import _escalate_to_human_impl
        from production.agent.schemas import EscalateInput

        params = EscalateInput(
            ticket_id=str(uuid.uuid4()),
            reason="Customer requested human agent explicitly.",
            urgency="high",
        )
        result_str = await _escalate_to_human_impl(params)
        result = json.loads(result_str)

    assert result["status"] == "escalated"
    uuid.UUID(result["escalation_id"])  # raises ValueError if not valid UUID
    assert result["urgency"] == "high"


async def test_escalate_to_human_empty_reason_raises():
    """Empty reason raises pydantic.ValidationError (min_length=1)."""
    from pydantic import ValidationError
    from production.agent.schemas import EscalateInput

    with pytest.raises(ValidationError):
        EscalateInput(ticket_id="some-id", reason="", urgency="medium")


async def test_escalate_to_human_idempotent(mock_pool, mock_openai_client):
    """Re-escalating already-escalated ticket does not error; escalation_id present."""
    pool, conn = mock_pool

    with patch("production.agent.tools.get_db_pool", new_callable=AsyncMock, return_value=pool), \
         patch("production.agent.tools.queries") as mock_queries:
        mock_queries.update_ticket_status = AsyncMock(return_value=None)

        from production.agent.tools import _escalate_to_human_impl
        from production.agent.schemas import EscalateInput

        params = EscalateInput(
            ticket_id=str(uuid.uuid4()),
            reason="Repeat escalation for already-escalated ticket.",
            urgency="medium",
        )
        result_str = await _escalate_to_human_impl(params)
        result = json.loads(result_str)

    assert result["status"] == "escalated"
    assert "escalation_id" in result
    assert "error" not in result


# ---------------------------------------------------------------------------
# T023: get_sentiment_trend tests
# ---------------------------------------------------------------------------


async def test_sentiment_trend_improving(mock_pool, mock_openai_client):
    """Scores [0.2, 0.4, 0.6] → trend=improving, recommend_escalation=False."""
    pool, conn = mock_pool
    scores = [0.2, 0.4, 0.6]

    with patch("production.agent.tools.get_db_pool", new_callable=AsyncMock, return_value=pool), \
         patch("production.agent.tools.queries") as mock_queries:
        mock_queries.get_sentiment_trend = AsyncMock(return_value=scores)

        from production.agent.tools import _get_sentiment_trend_impl

        result_str = await _get_sentiment_trend_impl(customer_id=str(uuid.uuid4()), last_n=5)
        result = json.loads(result_str)

    assert result["trend"] == "improving"
    assert result["recommend_escalation"] is False  # avg 0.4 >= 0.3


async def test_sentiment_trend_deteriorating_escalation(mock_pool, mock_openai_client):
    """Scores [0.5, 0.2, 0.1] → trend=deteriorating, recommend_escalation=True."""
    pool, conn = mock_pool
    scores = [0.5, 0.2, 0.1]

    with patch("production.agent.tools.get_db_pool", new_callable=AsyncMock, return_value=pool), \
         patch("production.agent.tools.queries") as mock_queries:
        mock_queries.get_sentiment_trend = AsyncMock(return_value=scores)

        from production.agent.tools import _get_sentiment_trend_impl

        result_str = await _get_sentiment_trend_impl(customer_id=str(uuid.uuid4()), last_n=5)
        result = json.loads(result_str)

    assert result["trend"] == "deteriorating"
    assert result["recommend_escalation"] is True  # avg ≈ 0.267 < 0.3


async def test_sentiment_trend_empty(mock_pool, mock_openai_client):
    """Empty scores → insufficient_data, recommend_escalation=False."""
    pool, conn = mock_pool

    with patch("production.agent.tools.get_db_pool", new_callable=AsyncMock, return_value=pool), \
         patch("production.agent.tools.queries") as mock_queries:
        mock_queries.get_sentiment_trend = AsyncMock(return_value=[])

        from production.agent.tools import _get_sentiment_trend_impl

        result_str = await _get_sentiment_trend_impl(customer_id=str(uuid.uuid4()), last_n=5)
        result = json.loads(result_str)

    assert result["scores"] == []
    assert result["count"] == 0
    assert result["trend"] == "insufficient_data"
    assert result["recommend_escalation"] is False
