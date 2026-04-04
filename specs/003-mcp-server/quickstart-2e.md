# Quickstart: Phase 2E — Agent Skills

**Branch**: `003-mcp-server` | **Date**: 2026-04-03

---

## What Was Built

Three new Python modules added to `src/agent/`:

| Module | Purpose |
|--------|---------|
| `skills_manifest.py` | 5 `SkillManifest` dataclass instances; `SKILLS` list |
| `skills_registry.py` | `SkillsRegistry` — `get_skill(skill_id)` / `list_skills()` |
| `skills_invoker.py` | `SkillsInvoker.run(msg)` + `apply_channel_adaptation()` |

`prototype.py::process_ticket` updated to delegate to `SkillsInvoker`.

---

## Import Examples

```python
# Inspect a skill manifest
from src.agent.skills_manifest import CUSTOMER_IDENTIFICATION
print(CUSTOMER_IDENTIFICATION.skill_id)    # "customer_identification_v1"
print(CUSTOMER_IDENTIFICATION.priority)   # 0

# List all skills in invocation order
from src.agent.skills_registry import get_registry
registry = get_registry()
for skill in registry.list_skills():
    print(f"{skill.priority}: {skill.name}")

# Look up by ID
manifest = registry.get_skill("escalation_decision_v1")
print(manifest.guardrails)

# Run the invoker directly (useful for testing)
from src.agent.skills_invoker import SkillsInvoker
from src.agent.models import TicketMessage, Channel

msg = TicketMessage(
    message="How do I connect NexaFlow to Slack?",
    channel=Channel.EMAIL,
    customer_email="test@example.com",
    customer_phone=None,
    customer_name="Test User",
)
invoker = SkillsInvoker()
result = invoker.run(msg)
print(result.customer_id_result.customer_id)
print(result.sentiment_result.trend_label)
print(result.escalation_result.should_escalate)
```

---

## Run Tests

```bash
# All tests (must stay at 79+ passing)
python -m pytest tests/ -v

# Skills-specific tests only
python -m pytest tests/test_skills.py -v
```

---

## No New Config or Environment Variables

Phase 2E adds no new environment variables, no new packages, and no new services.

---

## Invocation Order Reference

```
0. customer_identification_v1  → resolve_identity() + get_or_create_customer()
1. sentiment_analysis_v1       → compute_sentiment_trend()
2. knowledge_retrieval_v1      → KnowledgeBase.search()  [conditional]
3. escalation_decision_v1      → evaluate_escalation()
4. channel_adaptation_v1       → format_response()       [after LLM draft]
```
