# Quickstart: Phase 4B — Production Agent

**Branch**: `006-production-agent` | **Date**: 2026-04-04

---

## Prerequisites

```bash
# Environment variables required
export OPENAI_API_KEY=sk-...
export DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require

# Install dependencies (production/requirements.txt)
pip install openai-agents asyncpg pydantic python-dotenv

# Python 3.12 required
python --version  # must be 3.12+
```

---

## Run the Agent (Phase 4B stub delivery)

```python
import asyncio
from production.agent.customer_success_agent import process_ticket
from production.agent.customer_success_agent import CustomerContext

async def main():
    ctx = CustomerContext(
        customer_id="uuid-from-db",
        customer_name="Sarah Chen",
        customer_email="sarah@example.com",
        channel="web_form",
        message="How do I set up the Slack integration with my Growth plan?",
        conversation_id=None,  # triggers create_conversation
    )
    response = await process_ticket(ctx)
    print(f"ticket_id: {response.ticket_id}")
    print(f"escalated: {response.escalated}")
    print(f"status: {response.resolution_status}")
    print(response.response_text)

asyncio.run(main())
```

---

## Run Tests

```bash
# Unit tests (mocked — no DB or OpenAI API required)
pytest production/tests/test_agent_tools.py -v

# Integration tests (requires live DB)
TEST_DATABASE_URL=postgresql://... pytest production/tests/test_agent_integration.py -v

# All Phase 4 tests
pytest production/tests/ -v
```

---

## Key files

| File | Purpose |
|------|---------|
| `production/agent/tools.py` | 7 @function_tool definitions |
| `production/agent/prompts.py` | build_system_prompt() with PKT datetime |
| `production/agent/formatters.py` | 3 channel formatters + FormattedResponse |
| `production/agent/customer_success_agent.py` | Agent definition + process_ticket() |
| `production/database/queries.py` | 13 async DB functions (Phase 4A) |
| `production/tests/test_agent_tools.py` | Unit tests (mocked) |
| `production/tests/test_agent_integration.py` | Integration tests (live DB) |
