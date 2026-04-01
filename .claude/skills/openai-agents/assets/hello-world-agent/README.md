# Hello World Agent

Minimal example demonstrating the OpenAI Agents SDK fundamentals.

## What This Demonstrates

- **Basic agent creation** with instructions
- **Function tools** with `@function_tool` decorator
- **Structured outputs** with Pydantic models
- **Running agents** with `Runner.run()`
- **Usage tracking** with token metrics

## Quick Start

1. Install the SDK:
```bash
pip install openai-agents
```

2. Set your API key:
```bash
export OPENAI_API_KEY=sk-...
```

3. Run the example:
```bash
python main.py
```

## Code Structure

- `get_current_time()` - Simple tool without parameters
- `calculate()` - Tool with parameters and error handling
- `TaskResponse` - Pydantic model for structured output
- `simple_agent` - Agent with tools
- `structured_agent` - Agent with structured output
- `main()` - Examples of different interaction patterns

## Next Steps

- Add more tools for your use case
- Customize the agent instructions
- Add input/output guardrails
- Implement session management for multi-turn conversations
- Explore the multi-agent-workflow template for advanced patterns

## Learn More

See the OpenAI Agents SDK skill documentation for comprehensive patterns and examples.
