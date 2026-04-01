# Guardrails Patterns

Comprehensive patterns for implementing safety, validation, and control mechanisms with input and output guardrails.

## Table of Contents
- Guardrails Overview
- Input Guardrails
- Output Guardrails
- Tripwire Patterns
- Error Handling
- Advanced Guardrail Patterns

## Guardrails Overview

Guardrails provide safety and validation mechanisms for agent workflows:

**Input Guardrails**: Validate incoming requests before agent processing
**Output Guardrails**: Validate agent responses before delivery
**Tripwires**: Stop execution when conditions are met

### When to Use Guardrails

- **Safety-critical applications**: Prevent harmful or inappropriate interactions
- **Compliance requirements**: Enforce business rules and regulations
- **Quality control**: Ensure outputs meet standards
- **Access control**: Restrict certain capabilities based on conditions
- **Rate limiting**: Control resource usage
- **Content filtering**: Block prohibited content types

## Input Guardrails

Validate and filter requests before processing.

### Basic Input Guardrail

```python
from agents import Agent, Runner, InputGuardrail, GuardrailFunctionOutput
from agents.exceptions import InputGuardrailTripwireTriggered
import asyncio

async def check_appropriate_content(ctx, agent, input_data):
    """Check if input is appropriate."""

    # Simple keyword filter
    prohibited_keywords = ["harmful", "illegal", "dangerous"]
    input_text = input_data if isinstance(input_data, str) else str(input_data)

    has_prohibited = any(keyword in input_text.lower() for keyword in prohibited_keywords)

    return GuardrailFunctionOutput(
        output_info={"blocked": has_prohibited, "reason": "Prohibited content detected" if has_prohibited else "OK"},
        tripwire_triggered=has_prohibited  # Block if prohibited content found
    )

agent = Agent(
    name="Safe Assistant",
    instructions="Help users with appropriate requests.",
    input_guardrails=[InputGuardrail(guardrail_function=check_appropriate_content)]
)

async def main():
    try:
        result = await Runner.run(agent, "Help me with my homework")
        print(result.final_output)
    except InputGuardrailTripwireTriggered as e:
        print(f"⛔ Request blocked: {e.guardrail_result.output.output_info}")

asyncio.run(main())
```

### Input Guardrail with Agent-Based Validation

Use a specialized agent to perform complex validation:

```python
from pydantic import BaseModel, Field

class ContentCheck(BaseModel):
    is_appropriate: bool = Field(description="Whether content is appropriate")
    category: str = Field(description="Content category")
    reasoning: str = Field(description="Reasoning for the decision")

# Validation agent
content_checker = Agent(
    name="Content Checker",
    instructions="""Analyze input for appropriateness.
    Check for: violence, hate speech, illegal activities, spam.
    Return structured analysis.""",
    output_type=ContentCheck
)

async def content_validation_guardrail(ctx, agent, input_data):
    """Use agent to validate content."""

    result = await Runner.run(
        content_checker,
        f"Analyze this request: {input_data}",
        context=ctx.context
    )

    check = result.final_output_as(ContentCheck)

    return GuardrailFunctionOutput(
        output_info=check.model_dump(),
        tripwire_triggered=not check.is_appropriate  # Block inappropriate content
    )

protected_agent = Agent(
    name="Protected Agent",
    instructions="Assist users with appropriate requests.",
    input_guardrails=[InputGuardrail(guardrail_function=content_validation_guardrail)]
)
```

### Context-Aware Input Guardrail

Access context to make validation decisions:

```python
from dataclasses import dataclass

@dataclass
class UserContext:
    user_id: str
    role: str  # "admin", "user", "guest"
    subscription_tier: str  # "free", "pro", "enterprise"

async def permission_guardrail(ctx, agent, input_data):
    """Check user permissions based on context."""

    user_context = ctx.context
    input_lower = input_data.lower() if isinstance(input_data, str) else ""

    # Admin-only operations
    admin_keywords = ["delete all", "reset system", "modify settings"]
    requires_admin = any(keyword in input_lower for keyword in admin_keywords)

    if requires_admin and user_context.role != "admin":
        return GuardrailFunctionOutput(
            output_info={"denied": True, "reason": "Admin privileges required"},
            tripwire_triggered=True
        )

    # Pro features for paid users
    pro_keywords = ["export data", "advanced analytics", "batch process"]
    requires_pro = any(keyword in input_lower for keyword in pro_keywords)

    if requires_pro and user_context.subscription_tier == "free":
        return GuardrailFunctionOutput(
            output_info={"denied": True, "reason": "Pro subscription required"},
            tripwire_triggered=True
        )

    # Allow request
    return GuardrailFunctionOutput(
        output_info={"allowed": True},
        tripwire_triggered=False
    )

role_based_agent = Agent[UserContext](
    name="Role-Based Agent",
    instructions="Perform operations based on user permissions.",
    input_guardrails=[InputGuardrail(guardrail_function=permission_guardrail)]
)

async def main():
    # Free user context
    free_user = UserContext(user_id="user_123", role="user", subscription_tier="free")

    try:
        result = await Runner.run(
            role_based_agent,
            "Export all my data",
            context=free_user
        )
        print(result.final_output)
    except InputGuardrailTripwireTriggered as e:
        print(f"⛔ Access denied: {e.guardrail_result.output.output_info['reason']}")

asyncio.run(main())
```

### Multiple Input Guardrails

Chain multiple validation checks:

```python
async def rate_limit_guardrail(ctx, agent, input_data):
    """Check rate limits (simplified)."""
    # In production, check against Redis or database
    user_requests_today = 50  # Simulated

    if user_requests_today > 100:
        return GuardrailFunctionOutput(
            output_info={"rate_limited": True},
            tripwire_triggered=True
        )

    return GuardrailFunctionOutput(
        output_info={"rate_limited": False},
        tripwire_triggered=False
    )

async def size_limit_guardrail(ctx, agent, input_data):
    """Limit input size."""
    max_length = 5000
    input_text = str(input_data)

    if len(input_text) > max_length:
        return GuardrailFunctionOutput(
            output_info={"too_large": True, "size": len(input_text)},
            tripwire_triggered=True
        )

    return GuardrailFunctionOutput(
        output_info={"too_large": False},
        tripwire_triggered=False
    )

# Agent with multiple guardrails (executed in order)
multi_guarded_agent = Agent(
    name="Multi-Guarded Agent",
    instructions="Process requests with multiple safety checks.",
    input_guardrails=[
        InputGuardrail(guardrail_function=rate_limit_guardrail),
        InputGuardrail(guardrail_function=size_limit_guardrail),
        InputGuardrail(guardrail_function=content_validation_guardrail),
    ]
)
```

## Output Guardrails

Validate agent responses before delivery.

### Basic Output Guardrail

```python
from agents import OutputGuardrail
from agents.exceptions import OutputGuardrailTripwireTriggered

async def pii_filter_guardrail(ctx, agent, output):
    """Check output for PII (simplified)."""

    import re

    output_text = str(output)

    # Simple patterns (use real PII detection in production)
    ssn_pattern = r'\d{3}-\d{2}-\d{4}'
    credit_card_pattern = r'\d{4}-\d{4}-\d{4}-\d{4}'

    has_ssn = re.search(ssn_pattern, output_text)
    has_cc = re.search(credit_card_pattern, output_text)

    if has_ssn or has_cc:
        return GuardrailFunctionOutput(
            output_info={"pii_detected": True, "types": ["SSN" if has_ssn else None, "Credit Card" if has_cc else None]},
            tripwire_triggered=True  # Block output
        )

    return GuardrailFunctionOutput(
        output_info={"pii_detected": False},
        tripwire_triggered=False
    )

agent_with_output_guard = Agent(
    name="PII-Protected Agent",
    instructions="Provide information, but never include PII.",
    output_guardrails=[OutputGuardrail(guardrail_function=pii_filter_guardrail)]
)

async def main():
    try:
        result = await Runner.run(
            agent_with_output_guard,
            "What information do you have?"
        )
        print(result.final_output)
    except OutputGuardrailTripwireTriggered as e:
        print(f"⛔ Output blocked: PII detected - {e.guardrail_result.output.output_info}")

asyncio.run(main())
```

### Output Quality Guardrail

Ensure outputs meet quality standards:

```python
class QualityCheck(BaseModel):
    meets_standards: bool = Field(description="Whether output meets quality standards")
    issues: list[str] = Field(description="List of quality issues")
    score: int = Field(description="Quality score 0-100")

quality_checker = Agent(
    name="Quality Checker",
    instructions="""Evaluate output quality:
    - Clarity and coherence
    - Accuracy and relevance
    - Professional tone
    - Completeness
    Return structured quality assessment.""",
    output_type=QualityCheck
)

async def quality_guardrail(ctx, agent, output):
    """Validate output quality."""

    result = await Runner.run(
        quality_checker,
        f"Evaluate this response: {output}"
    )

    quality = result.final_output_as(QualityCheck)

    # Require minimum quality score
    if quality.score < 70:
        return GuardrailFunctionOutput(
            output_info=quality.model_dump(),
            tripwire_triggered=True  # Reject low-quality output
        )

    return GuardrailFunctionOutput(
        output_info=quality.model_dump(),
        tripwire_triggered=False
    )

quality_controlled_agent = Agent(
    name="Quality-Controlled Agent",
    instructions="Provide high-quality responses.",
    output_guardrails=[OutputGuardrail(guardrail_function=quality_guardrail)]
)
```

### Output Length Guardrail

Control response length:

```python
async def length_guardrail(ctx, agent, output):
    """Ensure output is within acceptable length."""

    output_text = str(output)
    min_length = 50
    max_length = 2000

    if len(output_text) < min_length:
        return GuardrailFunctionOutput(
            output_info={"too_short": True, "length": len(output_text)},
            tripwire_triggered=True
        )

    if len(output_text) > max_length:
        return GuardrailFunctionOutput(
            output_info={"too_long": True, "length": len(output_text)},
            tripwire_triggered=True
        )

    return GuardrailFunctionOutput(
        output_info={"length_ok": True, "length": len(output_text)},
        tripwire_triggered=False
    )

length_controlled_agent = Agent(
    name="Length-Controlled Agent",
    instructions="Provide responses between 50-2000 characters.",
    output_guardrails=[OutputGuardrail(guardrail_function=length_guardrail)]
)
```

## Tripwire Patterns

### Soft Tripwire (Log but Allow)

Log issues without blocking:

```python
async def monitoring_guardrail(ctx, agent, input_data):
    """Monitor input patterns without blocking."""

    # Check for concerning patterns
    suspicious_patterns = ["unusual pattern", "edge case"]
    input_text = str(input_data).lower()

    has_concerns = any(pattern in input_text for pattern in suspicious_patterns)

    if has_concerns:
        # Log for monitoring (in production, send to logging system)
        print(f"⚠️  Warning: Suspicious pattern detected in input")

    # Never trigger tripwire - just monitor
    return GuardrailFunctionOutput(
        output_info={"monitored": True, "concerns": has_concerns},
        tripwire_triggered=False  # Always allow
    )

monitored_agent = Agent(
    name="Monitored Agent",
    input_guardrails=[InputGuardrail(guardrail_function=monitoring_guardrail)]
)
```

### Progressive Tripwire

Escalate based on severity:

```python
async def severity_based_guardrail(ctx, agent, input_data):
    """Block based on severity level."""

    input_text = str(input_data).lower()

    # Categorize by severity
    critical_terms = ["critical", "severe"]
    warning_terms = ["warning", "caution"]

    has_critical = any(term in input_text for term in critical_terms)
    has_warning = any(term in input_text for term in warning_terms)

    if has_critical:
        # Critical issues: block
        return GuardrailFunctionOutput(
            output_info={"severity": "critical", "action": "blocked"},
            tripwire_triggered=True
        )
    elif has_warning:
        # Warnings: allow but flag
        print("⚠️  Warning-level content detected")
        return GuardrailFunctionOutput(
            output_info={"severity": "warning", "action": "allowed with flag"},
            tripwire_triggered=False
        )
    else:
        # Normal: allow
        return GuardrailFunctionOutput(
            output_info={"severity": "normal", "action": "allowed"},
            tripwire_triggered=False
        )
```

## Error Handling

### Comprehensive Exception Handling

```python
from agents.exceptions import (
    InputGuardrailTripwireTriggered,
    OutputGuardrailTripwireTriggered,
    MaxTurnsExceeded
)

async def safe_agent_run(agent, user_input, context=None):
    """Run agent with comprehensive error handling."""

    try:
        result = await Runner.run(
            agent,
            user_input,
            context=context,
            max_turns=10
        )
        return {
            "success": True,
            "output": result.final_output,
            "error": None
        }

    except InputGuardrailTripwireTriggered as e:
        # Input was blocked
        return {
            "success": False,
            "output": None,
            "error": {
                "type": "input_blocked",
                "reason": e.guardrail_result.output.output_info
            }
        }

    except OutputGuardrailTripwireTriggered as e:
        # Output was blocked
        return {
            "success": False,
            "output": None,
            "error": {
                "type": "output_blocked",
                "reason": e.guardrail_result.output.output_info
            }
        }

    except MaxTurnsExceeded as e:
        # Agent exceeded turn limit
        return {
            "success": False,
            "output": None,
            "error": {
                "type": "max_turns",
                "message": "Request too complex"
            }
        }

    except Exception as e:
        # Other errors
        return {
            "success": False,
            "output": None,
            "error": {
                "type": "unknown",
                "message": str(e)
            }
        }

# Usage
async def main():
    result = await safe_agent_run(protected_agent, "User request")

    if result["success"]:
        print(f"Output: {result['output']}")
    else:
        print(f"Error ({result['error']['type']}): {result['error']}")
```

### Retry with Fallback

```python
async def run_with_retry(agent, user_input, max_retries=3):
    """Retry on output guardrail failures."""

    for attempt in range(max_retries):
        try:
            result = await Runner.run(agent, user_input)
            return result.final_output

        except OutputGuardrailTripwireTriggered as e:
            print(f"Attempt {attempt + 1} failed: {e.guardrail_result.output.output_info}")

            if attempt == max_retries - 1:
                # Final attempt failed
                raise

            # Retry with modified prompt
            user_input = f"{user_input}\n[Previous attempt had issues. Please revise.]"

        except InputGuardrailTripwireTriggered:
            # Input issues can't be retried
            raise

    return None
```

## Advanced Guardrail Patterns

### Tool-Level Guardrails

Apply guardrails to specific tools:

```python
from agents import ToolInputGuardrail, ToolOutputGuardrail

async def tool_input_check(ctx, agent, tool_name, tool_arguments):
    """Validate tool arguments before execution."""

    # Example: Prevent deletion of critical data
    if tool_name == "delete_data":
        if tool_arguments.get("data_id", "").startswith("critical_"):
            return GuardrailFunctionOutput(
                output_info={"blocked": True, "reason": "Cannot delete critical data"},
                tripwire_triggered=True
            )

    return GuardrailFunctionOutput(
        output_info={"allowed": True},
        tripwire_triggered=False
    )

async def tool_output_check(ctx, agent, tool_name, tool_output):
    """Validate tool output before returning to agent."""

    # Example: Ensure data is not empty
    if not tool_output or len(str(tool_output)) == 0:
        return GuardrailFunctionOutput(
            output_info={"empty_output": True},
            tripwire_triggered=True
        )

    return GuardrailFunctionOutput(
        output_info={"valid_output": True},
        tripwire_triggered=False
    )

@function_tool(
    tool_input_guardrails=[ToolInputGuardrail(guardrail_function=tool_input_check)],
    tool_output_guardrails=[ToolOutputGuardrail(guardrail_function=tool_output_check)]
)
def protected_tool(data_id: str) -> str:
    """Tool with input and output guards.

    Args:
        data_id: The data ID to process
    """
    return f"Processed: {data_id}"
```

### Composite Guardrails

Combine multiple checks efficiently:

```python
class GuardrailChecker:
    """Reusable guardrail logic."""

    @staticmethod
    async def check_content_safety(text: str) -> tuple[bool, str]:
        """Check if content is safe."""
        # Simulated - use real content moderation API
        prohibited = ["spam", "scam"]
        is_safe = not any(word in text.lower() for word in prohibited)
        reason = "Safe" if is_safe else "Prohibited content detected"
        return is_safe, reason

    @staticmethod
    async def check_length(text: str, min_len: int, max_len: int) -> tuple[bool, str]:
        """Check length constraints."""
        length = len(text)
        if length < min_len:
            return False, f"Too short ({length} < {min_len})"
        if length > max_len:
            return False, f"Too long ({length} > {max_len})"
        return True, "Length OK"

    @staticmethod
    async def check_format(text: str, required_keywords: list[str]) -> tuple[bool, str]:
        """Check format requirements."""
        has_all = all(keyword in text.lower() for keyword in required_keywords)
        return has_all, "Format OK" if has_all else "Missing required keywords"

async def composite_guardrail(ctx, agent, input_data):
    """Run multiple checks."""

    text = str(input_data)
    checker = GuardrailChecker()

    # Run all checks
    is_safe, safety_msg = await checker.check_content_safety(text)
    is_valid_length, length_msg = await checker.check_length(text, 10, 1000)
    # Add more checks as needed

    # Collect all issues
    issues = []
    if not is_safe:
        issues.append(safety_msg)
    if not is_valid_length:
        issues.append(length_msg)

    # Trigger if any check failed
    triggered = len(issues) > 0

    return GuardrailFunctionOutput(
        output_info={"passed": not triggered, "issues": issues},
        tripwire_triggered=triggered
    )
```

## Best Practices

1. **Layer guardrails** - Use multiple complementary checks
2. **Fail gracefully** - Provide helpful error messages
3. **Log for monitoring** - Track guardrail triggers for analysis
4. **Context-aware** - Use context for permission/role checks
5. **Performance** - Keep guardrails fast, use caching
6. **Test thoroughly** - Verify guardrails work as intended
7. **Avoid over-filtering** - Balance safety with usability
8. **Use structured outputs** - Pydantic models for complex validation
9. **Separate concerns** - Different guardrails for different checks
10. **Document behavior** - Clear explanation of what triggers blocks
