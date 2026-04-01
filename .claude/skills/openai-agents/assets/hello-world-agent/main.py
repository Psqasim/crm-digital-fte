"""
Hello World Agent - Minimal OpenAI Agents SDK Example

This template demonstrates a simple agent with tools and structured output.
Perfect starting point for building your first agent.
"""

import asyncio
from agents import Agent, Runner, function_tool
from pydantic import BaseModel, Field


# Define a simple tool
@function_tool
def get_current_time() -> str:
    """Get the current time.

    Returns:
        Current time as a formatted string
    """
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@function_tool
def calculate(expression: str) -> str:
    """Calculate a mathematical expression safely.

    Args:
        expression: Mathematical expression to evaluate (e.g., "2 + 2")

    Returns:
        Result of the calculation
    """
    try:
        # Safe evaluation (limited scope)
        result = eval(expression, {"__builtins__": {}}, {})
        return f"{expression} = {result}"
    except Exception as e:
        return f"Error calculating {expression}: {str(e)}"


# Define structured output model
class TaskResponse(BaseModel):
    """Structured response for task completion."""
    task_completed: bool = Field(description="Whether the task was completed")
    result: str = Field(description="The result or answer")
    confidence: str = Field(description="Confidence level: high, medium, low")


# Create agent with tools
simple_agent = Agent(
    name="Hello World Agent",
    instructions="""You are a helpful assistant that can:
    - Tell the current time
    - Perform calculations
    - Answer general questions

    Be concise and friendly.""",
    tools=[get_current_time, calculate]
)

# Create agent with structured output
structured_agent = Agent(
    name="Structured Agent",
    instructions="Process tasks and return structured responses.",
    output_type=TaskResponse
)


async def main():
    """Run example agent interactions."""

    print("=" * 60)
    print("OpenAI Agents SDK - Hello World Example")
    print("=" * 60)

    # Example 1: Simple agent with tools
    print("\n1. Simple Agent with Tools:")
    print("-" * 60)

    result = await Runner.run(
        simple_agent,
        "What time is it? Also, what is 15 * 23?"
    )

    print(f"User: What time is it? Also, what is 15 * 23?")
    print(f"Agent: {result.final_output}")
    print(f"\nUsage: {result.usage.total_tokens} tokens")

    # Example 2: Structured output agent
    print("\n2. Structured Output Agent:")
    print("-" * 60)

    result = await Runner.run(
        structured_agent,
        "What is the capital of France?"
    )

    # Access typed output
    response = result.final_output_as(TaskResponse)
    print(f"User: What is the capital of France?")
    print(f"Task Completed: {response.task_completed}")
    print(f"Result: {response.result}")
    print(f"Confidence: {response.confidence}")

    # Example 3: Multi-turn with simple prompt-based flow
    print("\n3. Sequential Queries:")
    print("-" * 60)

    queries = [
        "Calculate 100 divided by 5",
        "What is 20% of that result?",
    ]

    for query in queries:
        result = await Runner.run(simple_agent, query)
        print(f"User: {query}")
        print(f"Agent: {result.final_output}\n")

    print("=" * 60)
    print("Examples completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
