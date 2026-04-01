"""
Multi-Agent Workflow - Complete OpenAI Agents SDK Example

This template demonstrates a realistic multi-agent system with:
- Triage routing
- Specialized agents
- Handoffs between agents
- Shared session for conversation history
- Input guardrails
- Error handling
"""

import asyncio
from agents import (
    Agent,
    Runner,
    SQLiteSession,
    InputGuardrail,
    GuardrailFunctionOutput,
    function_tool
)
from agents.exceptions import InputGuardrailTripwireTriggered
from pydantic import BaseModel, Field


# ============================================================================
# GUARDRAILS
# ============================================================================

class ContentCheck(BaseModel):
    """Content validation result."""
    is_appropriate: bool = Field(description="Whether content is appropriate")
    reason: str = Field(description="Reason for the decision")


content_checker = Agent(
    name="Content Checker",
    instructions="""Analyze user input for appropriateness.
    Block: spam, abuse, harmful content, off-topic requests.
    Allow: legitimate support and technical questions.""",
    output_type=ContentCheck
)


async def content_guardrail(ctx, agent, input_data):
    """Validate input before processing."""
    result = await Runner.run(content_checker, f"Check: {input_data}")
    check = result.final_output_as(ContentCheck)

    return GuardrailFunctionOutput(
        output_info=check.model_dump(),
        tripwire_triggered=not check.is_appropriate
    )


# ============================================================================
# TOOLS
# ============================================================================

@function_tool
def lookup_account(account_id: str) -> str:
    """Look up account information.

    Args:
        account_id: The account ID to look up

    Returns:
        Account information
    """
    # Simulated - replace with real database lookup
    accounts = {
        "ACC-123": "Account: Premium tier, active since 2024",
        "ACC-456": "Account: Free tier, active since 2025",
    }
    return accounts.get(account_id, "Account not found")


@function_tool
def check_system_status() -> str:
    """Check system status.

    Returns:
        Current system status
    """
    # Simulated - replace with real health check
    return "All systems operational. API: ✓, Database: ✓, Services: ✓"


@function_tool
def create_support_ticket(issue: str, priority: str = "normal") -> str:
    """Create a support ticket.

    Args:
        issue: Description of the issue
        priority: Priority level (low, normal, high, urgent)

    Returns:
        Ticket ID
    """
    # Simulated - replace with real ticketing system
    ticket_id = f"TICKET-{abs(hash(issue)) % 10000:04d}"
    return f"Created ticket {ticket_id} with {priority} priority"


# ============================================================================
# SPECIALIZED AGENTS
# ============================================================================

technical_support = Agent(
    name="Technical Support",
    handoff_description="Handles technical issues, bugs, and troubleshooting",
    instructions="""You are a technical support specialist.

    Help users with:
    - Technical problems and errors
    - Troubleshooting steps
    - System status checks
    - Bug reports

    Use available tools to check system status and create tickets for unresolved issues.
    Be thorough and provide step-by-step guidance.""",
    tools=[check_system_status, create_support_ticket]
)

account_support = Agent(
    name="Account Support",
    handoff_description="Handles account questions, billing, and subscriptions",
    instructions="""You are an account support specialist.

    Help users with:
    - Account information and settings
    - Billing and payment questions
    - Subscription management
    - Account access issues

    Use the lookup_account tool to retrieve account details.
    Be helpful and professional.""",
    tools=[lookup_account, create_support_ticket]
)

general_support = Agent(
    name="General Support",
    handoff_description="Handles general questions and information requests",
    instructions="""You are a general support specialist.

    Help users with:
    - Product information
    - How-to questions
    - General inquiries
    - Documentation references

    Provide clear, concise answers. Create tickets for complex issues.""",
    tools=[create_support_ticket]
)


# ============================================================================
# TRIAGE AGENT
# ============================================================================

triage_agent = Agent(
    name="Support Triage",
    instructions="""You are the first point of contact for customer support.

    Analyze the user's request and route to the appropriate specialist:

    - **Technical Support**: Bugs, errors, technical problems, system issues
    - **Account Support**: Billing, payments, subscriptions, account settings
    - **General Support**: Product questions, how-to guides, general inquiries

    Choose the most appropriate specialist based on the request.""",
    handoffs=[technical_support, account_support, general_support],
    input_guardrails=[InputGuardrail(guardrail_function=content_guardrail)]
)


# ============================================================================
# MAIN APPLICATION
# ============================================================================

async def handle_support_request(user_input: str, session_id: str = "default"):
    """
    Handle a support request through the multi-agent system.

    Args:
        user_input: The user's support request
        session_id: Session ID for conversation history

    Returns:
        Response from the appropriate agent
    """
    # Create session for conversation history
    session = SQLiteSession(session_id, "support_sessions.db")

    try:
        # Run through triage (may hand off to specialist)
        result = await Runner.run(
            triage_agent,
            user_input,
            session=session,
            max_turns=10
        )

        return {
            "success": True,
            "response": result.final_output,
            "tokens_used": result.usage.total_tokens
        }

    except InputGuardrailTripwireTriggered as e:
        # Input was blocked by guardrail
        reason = e.guardrail_result.output.output_info.get("reason", "Inappropriate content")
        return {
            "success": False,
            "error": "input_blocked",
            "message": f"Request blocked: {reason}"
        }

    except Exception as e:
        # Other errors
        return {
            "success": False,
            "error": "processing_error",
            "message": f"Error processing request: {str(e)}"
        }


async def main():
    """Run example multi-agent workflows."""

    print("=" * 70)
    print("Multi-Agent Support System - OpenAI Agents SDK")
    print("=" * 70)

    # Example requests
    examples = [
        {
            "request": "My app keeps crashing when I upload files",
            "description": "Technical issue → Technical Support"
        },
        {
            "request": "Can you check my account ACC-123?",
            "description": "Account inquiry → Account Support"
        },
        {
            "request": "How do I export my data?",
            "description": "General question → General Support"
        },
        {
            "request": "The API is returning error 500",
            "description": "Technical issue → Technical Support"
        }
    ]

    # Process each example
    for i, example in enumerate(examples, 1):
        print(f"\n{'='*70}")
        print(f"Example {i}: {example['description']}")
        print(f"{'='*70}")
        print(f"User: {example['request']}")
        print()

        # Handle request
        result = await handle_support_request(
            example["request"],
            session_id=f"example_{i}"
        )

        if result["success"]:
            print(f"Agent: {result['response']}")
            print(f"\n📊 Tokens used: {result['tokens_used']}")
        else:
            print(f"❌ Error ({result['error']}): {result['message']}")

    # Example: Multi-turn conversation
    print(f"\n{'='*70}")
    print("Multi-Turn Conversation Example")
    print(f"{'='*70}")

    session_id = "conversation_example"

    # Turn 1
    print("\n[Turn 1]")
    print("User: I'm having issues with my account")
    result = await handle_support_request(
        "I'm having issues with my account",
        session_id=session_id
    )
    if result["success"]:
        print(f"Agent: {result['response']}")

    # Turn 2 - Agent remembers context
    print("\n[Turn 2]")
    print("User: It's account ACC-456")
    result = await handle_support_request(
        "It's account ACC-456",
        session_id=session_id
    )
    if result["success"]:
        print(f"Agent: {result['response']}")

    print(f"\n{'='*70}")
    print("Examples completed successfully!")
    print(f"{'='*70}")


if __name__ == "__main__":
    asyncio.run(main())
