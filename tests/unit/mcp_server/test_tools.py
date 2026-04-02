"""
test_tools.py — Direct-import unit tests for all 7 MCP tools (Phase 2D).

Strategy: import tool coroutines from server.py and call via asyncio.run().
No MCP client required. autouse fixture resets the ConversationStore singleton
between every test to ensure hermetic isolation.
"""
from __future__ import annotations

import asyncio
import json

import pytest

from src.agent.conversation_store import reset_store
from src.mcp_server.server import (
    _ticket_index,
    create_ticket,
    escalate_to_human,
    get_customer_history,
    get_sentiment_trend,
    resolve_ticket,
    search_knowledge_base,
    send_response,
    store,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    """Reset the ConversationStore singleton and ticket index before every test."""
    _ticket_index.clear()
    reset_store()
    # Re-bind module-level `store` reference to fresh instance
    import src.mcp_server.server as srv
    from src.agent.conversation_store import get_store
    srv.store = get_store()
    yield
    _ticket_index.clear()
    reset_store()


# ---------------------------------------------------------------------------
# T005 — Smoke import test
# ---------------------------------------------------------------------------


def test_server_imports_without_error():
    """All 7 tool names must be callable."""
    tools = [
        search_knowledge_base,
        create_ticket,
        get_customer_history,
        escalate_to_human,
        send_response,
        get_sentiment_trend,
        resolve_ticket,
    ]
    for tool in tools:
        assert callable(tool), f"{tool} is not callable"


# ---------------------------------------------------------------------------
# T006 — US1: search_knowledge_base
# ---------------------------------------------------------------------------


def test_search_returns_ranked_results():
    result = asyncio.run(search_knowledge_base("workflow automation triggers"))
    data = json.loads(result)
    assert "results" in data
    assert data["count"] >= 0
    assert isinstance(data["results"], list)
    # Results may be empty if KB has no match, but structure must be correct
    for item in data["results"]:
        assert "section_title" in item
        assert "content" in item
        assert "relevance_score" in item


def test_search_no_match_returns_empty():
    result = asyncio.run(search_knowledge_base("xyzzy nonsense gibberish qqqq"))
    data = json.loads(result)
    # May return 0-score results or empty — key check: no "error" key
    assert "error" not in data
    assert "results" in data
    assert "count" in data


def test_search_empty_query_returns_validation_error():
    result = asyncio.run(search_knowledge_base(""))
    data = json.loads(result)
    assert "error" in data
    assert "validation" in data["error"]
    assert data["tool"] == "search_knowledge_base"


# ---------------------------------------------------------------------------
# T008 — US2: create_ticket
# ---------------------------------------------------------------------------


def test_create_ticket_returns_id():
    result = asyncio.run(
        create_ticket("user@example.com", "API not working", "high", "email")
    )
    data = json.loads(result)
    assert "ticket_id" in data
    assert data["ticket_id"].startswith("TKT-")
    assert data["status"] == "open"
    assert data["channel"] == "email"
    # _ticket_index must be populated
    assert data["ticket_id"] in _ticket_index


def test_create_ticket_new_customer():
    result = asyncio.run(
        create_ticket("newcustomer@test.com", "Cannot login", "low", "web_form")
    )
    data = json.loads(result)
    assert "ticket_id" in data
    assert "error" not in data


def test_create_ticket_invalid_channel():
    result = asyncio.run(
        create_ticket("user@example.com", "Issue", "high", "fax")
    )
    data = json.loads(result)
    assert "error" in data
    assert "validation" in data["error"]
    assert data["tool"] == "create_ticket"


def test_create_ticket_invalid_priority():
    result = asyncio.run(
        create_ticket("user@example.com", "Issue", "urgent", "email")
    )
    data = json.loads(result)
    assert "error" in data
    assert "validation" in data["error"]
    assert data["tool"] == "create_ticket"


def test_create_ticket_empty_issue():
    result = asyncio.run(
        create_ticket("user@example.com", "", "high", "email")
    )
    data = json.loads(result)
    assert "error" in data
    assert "validation" in data["error"]
    assert data["tool"] == "create_ticket"


# ---------------------------------------------------------------------------
# T010 — US5: send_response
# ---------------------------------------------------------------------------


def _make_ticket(customer_id: str = "user@example.com", channel: str = "email") -> str:
    """Helper: create a ticket and return ticket_id."""
    result = asyncio.run(
        create_ticket(customer_id, "Test issue", "medium", channel)
    )
    return json.loads(result)["ticket_id"]


def test_send_response_success():
    ticket_id = _make_ticket()
    result = asyncio.run(
        send_response(ticket_id, "Hello, here is your answer.", "email")
    )
    data = json.loads(result)
    assert data["delivery_status"] == "delivered"
    assert "channel" in data
    assert "timestamp" in data


def test_send_response_invalid_channel():
    ticket_id = _make_ticket()
    result = asyncio.run(send_response(ticket_id, "Hi", "sms"))
    data = json.loads(result)
    assert "error" in data
    assert "validation" in data["error"]
    assert data["tool"] == "send_response"


def test_send_response_empty_message():
    ticket_id = _make_ticket()
    result = asyncio.run(send_response(ticket_id, "", "email"))
    data = json.loads(result)
    assert "error" in data
    assert "validation" in data["error"]
    assert data["tool"] == "send_response"


def test_send_response_unknown_ticket():
    result = asyncio.run(send_response("TKT-notreal", "Hello", "email"))
    data = json.loads(result)
    assert "error" in data
    assert "not found" in data["error"]


# ---------------------------------------------------------------------------
# T012 — US3: get_customer_history
# ---------------------------------------------------------------------------


def test_history_multichannel():
    # Create two tickets on different channels for the same customer
    asyncio.run(create_ticket("multi@example.com", "Email issue", "low", "email"))
    # Resolve first ticket so a new conversation can be created
    import src.mcp_server.server as srv
    from src.agent.models import TicketStatus
    customer = srv.store.get_customer("multi@example.com")
    assert customer is not None
    conv_ids = customer.conversation_ids[:]
    if conv_ids:
        try:
            srv.store.transition_ticket(conv_ids[-1], TicketStatus.RESOLVED)
        except ValueError:
            pass
    asyncio.run(create_ticket("multi@example.com", "WhatsApp issue", "low", "whatsapp"))
    result = asyncio.run(get_customer_history("multi@example.com"))
    data = json.loads(result)
    assert data["conversation_count"] >= 1
    channels = data["channels_used"]
    assert "email" in channels


def test_history_unknown_customer():
    result = asyncio.run(get_customer_history("nobody@example.com"))
    data = json.loads(result)
    assert "error" not in data
    assert data["conversation_count"] == 0
    assert data["conversations"] == []


def test_history_empty_customer_id():
    result = asyncio.run(get_customer_history(""))
    data = json.loads(result)
    assert "error" in data
    assert "validation" in data["error"]
    assert data["tool"] == "get_customer_history"


# ---------------------------------------------------------------------------
# T014 — US4: escalate_to_human
# ---------------------------------------------------------------------------


def test_escalate_success():
    ticket_id = _make_ticket()
    result = asyncio.run(escalate_to_human(ticket_id, "Customer requested human agent"))
    data = json.loads(result)
    assert "escalation_id" in data
    assert data["escalation_id"].startswith("ESC-")
    assert data["status"] == "escalated"


def test_escalate_unknown_ticket():
    result = asyncio.run(escalate_to_human("TKT-unknown99", "reason"))
    data = json.loads(result)
    assert "error" in data
    assert "not found" in data["error"]


def test_escalate_already_escalated():
    ticket_id = _make_ticket()
    # First escalation — should succeed
    asyncio.run(escalate_to_human(ticket_id, "First escalation"))
    # Second escalation — must not raise; must return error JSON (invalid transition)
    result = asyncio.run(escalate_to_human(ticket_id, "Second escalation"))
    data = json.loads(result)
    assert "error" in data
    assert data["tool"] == "escalate_to_human"


# ---------------------------------------------------------------------------
# T016 — US7: resolve_ticket
# ---------------------------------------------------------------------------


def test_resolve_success():
    ticket_id = _make_ticket()
    result = asyncio.run(resolve_ticket(ticket_id, "Reset the API token and it worked."))
    data = json.loads(result)
    assert data["status"] == "resolved"
    assert "resolution_summary" in data
    assert "resolved_at" in data


def test_resolve_already_resolved_idempotent():
    ticket_id = _make_ticket()
    asyncio.run(resolve_ticket(ticket_id, "Fixed first time"))
    # Second call — must not raise; must return idempotent JSON with note field
    result = asyncio.run(resolve_ticket(ticket_id, "Fixed again"))
    data = json.loads(result)
    assert data["status"] == "resolved"
    assert "note" in data
    assert "error" not in data


def test_resolve_empty_summary():
    ticket_id = _make_ticket()
    result = asyncio.run(resolve_ticket(ticket_id, ""))
    data = json.loads(result)
    assert "error" in data
    assert "validation" in data["error"]
    assert data["tool"] == "resolve_ticket"


def test_resolve_unknown_ticket():
    result = asyncio.run(resolve_ticket("TKT-ghost", "Resolved somehow"))
    data = json.loads(result)
    assert "error" in data
    assert "not found" in data["error"]


# ---------------------------------------------------------------------------
# T018 — US6: get_sentiment_trend
# ---------------------------------------------------------------------------


def test_sentiment_insufficient_data():
    ticket_id = _make_ticket("sentiment@example.com")
    result = asyncio.run(get_sentiment_trend("sentiment@example.com"))
    data = json.loads(result)
    # With no scored inbound messages → insufficient data, stable
    assert data["trend"] == "stable"
    assert "note" in data


def test_sentiment_unknown_customer():
    result = asyncio.run(get_sentiment_trend("ghost@example.com"))
    data = json.loads(result)
    assert "error" not in data
    assert data["trend"] == "stable"
    assert data["window_scores"] == []
    assert data["recommend_escalation"] is False


def test_sentiment_empty_customer_id():
    result = asyncio.run(get_sentiment_trend(""))
    data = json.loads(result)
    assert "error" in data
    assert "validation" in data["error"]
    assert data["tool"] == "get_sentiment_trend"


# ---------------------------------------------------------------------------
# T020 — Cross-tool integration: all tools on fresh store
# ---------------------------------------------------------------------------


def test_fresh_store_all_tools_no_crash():
    """On a fresh empty store, every tool must return a valid JSON string."""
    # All tools return str — never raise
    tools_and_args = [
        (search_knowledge_base, ("billing",)),
        (create_ticket, ("fresh@example.com", "Test", "low", "email")),
        (get_customer_history, ("fresh@example.com",)),
        (send_response, ("TKT-fake", "hello", "email")),
        (escalate_to_human, ("TKT-fake", "reason")),
        (resolve_ticket, ("TKT-fake", "summary")),
        (get_sentiment_trend, ("fresh@example.com",)),
    ]
    for tool, args in tools_and_args:
        result = asyncio.run(tool(*args))
        assert isinstance(result, str), f"{tool.__name__} did not return str"
        parsed = json.loads(result)
        assert isinstance(parsed, dict), f"{tool.__name__} result is not a JSON object"
