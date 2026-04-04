from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from src.agent.models import EscalationDecision

load_dotenv(Path(__file__).parent.parent.parent / ".env")

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        _client = OpenAI(api_key=api_key)
    return _client


_ESCALATION_SYSTEM_PROMPT = """You are an escalation classifier for a B2B SaaS customer support system.

Your task: analyze the customer message and decide if it requires human agent escalation.

Escalate to a human when the customer's INTENT matches any of these:
1. Extreme negative emotion — customer appears very upset, angry, or frustrated (not just slightly annoyed)
2. Explicit request to speak with a human, manager, supervisor, or senior engineer
3. Refund request — customer wants their money back
4. Legal or compliance concern — GDPR, data privacy, DPA, sub-processors, legal action
5. Data breach or security incident — customer suspects unauthorized access or data exposure
6. Pricing negotiation — customer is asking for custom pricing, discounts on existing plan, or threatening to leave for pricing reasons
7. Three or more unanswered follow-ups — customer indicates they have contacted support multiple times without resolution
8. Enterprise SLA breach risk — customer on Enterprise plan whose issue is time-critical under 4-hour SLA

Do NOT escalate for:
- Standard technical questions, how-to requests, billing information questions
- A customer asking about charges or prorated billing (that is information, not a refund request)
- Minor frustration or impatience without explicit escalation triggers above
- General feature questions, onboarding help, export or integration setup

Use INTENT, not keywords. A customer asking "will I be charged" is NOT a refund request.
A customer saying "I demand a manager" IS an explicit human request.

Respond ONLY with a valid JSON object. No markdown fences. No explanation outside the JSON.

JSON schema:
{
  "should_escalate": true | false,
  "reason": "<concise reason code or phrase, max 50 chars>",
  "urgency": "low" | "normal" | "high"
}

Urgency rules:
- "high": data breach, security incident, Enterprise SLA breach risk
- "normal": refund, legal/compliance, explicit human request, multiple follow-ups, extreme sentiment
- "low": pricing negotiation only
- If should_escalate is false, use "normal" as default urgency."""


def evaluate_escalation(message: str) -> EscalationDecision:
    """Use GPT-4o-mini to classify whether the message requires human escalation.

    Returns an EscalationDecision. Never raises on parse errors — returns a safe
    default with should_escalate=True if the LLM response cannot be parsed.
    """
    client = _get_client()

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": _ESCALATION_SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ],
        temperature=0,
        max_tokens=150,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content or "{}"

    try:
        data = json.loads(raw)
        return EscalationDecision(
            should_escalate=bool(data.get("should_escalate", False)),
            reason=str(data.get("reason", "unknown")),
            urgency=str(data.get("urgency", "normal")),
            raw_llm_response=raw,
        )
    except (json.JSONDecodeError, KeyError):
        # Safe default: escalate if parse fails (fail open for safety)
        return EscalationDecision(
            should_escalate=True,
            reason="parse_error",
            urgency="normal",
            raw_llm_response=raw,
        )
