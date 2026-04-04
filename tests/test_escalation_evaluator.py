"""
T007 — Test stubs for escalation_evaluator.
These tests FAIL before T008 is implemented.
"""
import json
import pytest


# TKT-006: furious customer + explicit human request
TKT_006_TEXT = (
    "I am absolutely furious right now. For the THIRD time this week, all my automation rules "
    "have stopped firing. I have an entire operations team of 12 people whose workflows depend "
    "on this. We missed two critical deadlines because your system failed. I've already emailed "
    "twice this week with no resolution. I demand to speak to a manager or senior engineer "
    "immediately. If this isn't resolved today I am cancelling our Growth subscription and "
    "disputing the charge."
)

# TKT-003: billing question — should NOT escalate (no false positive)
TKT_003_TEXT = (
    "Hi, I want to upgrade from Starter to Growth plan. We now have 8 team members. "
    "Will the upgrade take effect immediately? Will I be charged for the full month or prorated? "
    "Also, can I get an invoice sent to our company GST number?"
)

# TKT-044: GDPR / legal compliance
TKT_044_TEXT = (
    "We are a UK-based company subject to GDPR. Before we can fully adopt NexaFlow we need to "
    "understand your data processing practices. Specifically: Where is our data stored? "
    "Do you have a Data Processing Agreement (DPA) available? Can we request deletion of all our data? "
    "What are your sub-processors? We may need to provide this to our DPO."
)


def test_tkt006_should_escalate():
    """TKT-006 (furious + explicit human request) → should_escalate=True, reason mentions sentiment or human-request."""
    from src.agent.escalation_evaluator import evaluate_escalation

    result = evaluate_escalation(TKT_006_TEXT)

    assert result.should_escalate is True, f"Expected escalation for furious customer; got: {result.reason}"
    reason_lower = result.reason.lower()
    assert any(kw in reason_lower for kw in ("sentiment", "human", "manager", "angry", "furious", "escalat")), (
        f"Reason should mention sentiment or human-request; got: {result.reason!r}"
    )


def test_tkt003_should_not_escalate():
    """TKT-003 (billing question with 'charged') → should_escalate=False (LLM intent beats keyword)."""
    from src.agent.escalation_evaluator import evaluate_escalation

    result = evaluate_escalation(TKT_003_TEXT)

    assert result.should_escalate is False, (
        f"Billing question should NOT escalate; reason: {result.reason!r}"
    )


def test_tkt044_gdpr_should_escalate():
    """TKT-044 (GDPR) → should_escalate=True, reason mentions legal/compliance."""
    from src.agent.escalation_evaluator import evaluate_escalation

    result = evaluate_escalation(TKT_044_TEXT)

    assert result.should_escalate is True, f"Expected GDPR to escalate; got: {result.reason}"
    reason_lower = result.reason.lower()
    assert any(kw in reason_lower for kw in ("legal", "compliance", "gdpr", "privacy", "data")), (
        f"Reason should mention legal/compliance; got: {result.reason!r}"
    )


def test_raw_llm_response_is_valid_json():
    """raw_llm_response must be parseable as JSON."""
    from src.agent.escalation_evaluator import evaluate_escalation

    result = evaluate_escalation(TKT_006_TEXT)

    parsed = json.loads(result.raw_llm_response)
    assert isinstance(parsed, dict), "raw_llm_response should be a JSON object"
