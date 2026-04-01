# Multi-Agent Workflow Template

Complete example of a production-ready multi-agent system with triage, routing, and specialist agents.

## What This Demonstrates

- **Triage pattern** - Route requests to appropriate specialists
- **Peer handoffs** - Agents hand off control to domain experts
- **Shared sessions** - Conversation history across agents
- **Input guardrails** - Content validation before processing
- **Tools per specialist** - Each agent has relevant capabilities
- **Error handling** - Robust exception management
- **Multi-turn conversations** - Context maintained across turns

## Architecture

```
User Request
    ↓
Content Guardrail (validates input)
    ↓
Triage Agent (analyzes & routes)
    ↓
    ├─→ Technical Support (bugs, errors, system issues)
    ├─→ Account Support (billing, subscriptions, account)
    └─→ General Support (product questions, how-to)
```

## Quick Start

1. Install dependencies:
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

### Guardrails
- `content_checker` - Agent that validates input appropriateness
- `content_guardrail()` - Input guardrail function

### Tools
- `lookup_account()` - Retrieve account information
- `check_system_status()` - System health check
- `create_support_ticket()` - Create support tickets

### Agents
- `triage_agent` - Routes to specialists, has input guardrail
- `technical_support` - Handles technical issues
- `account_support` - Handles account/billing questions
- `general_support` - Handles general inquiries

### Application
- `handle_support_request()` - Main entry point with error handling
- `main()` - Example workflows and multi-turn conversations

## Customization

### Add New Specialist

```python
custom_specialist = Agent(
    name="Custom Specialist",
    handoff_description="Handles custom domain questions",
    instructions="Your specialist instructions...",
    tools=[your_tools]
)

# Add to triage handoffs
triage_agent = Agent(
    # ... other config ...
    handoffs=[technical_support, account_support, general_support, custom_specialist]
)
```

### Add Custom Tool

```python
@function_tool
def your_custom_tool(param: str) -> str:
    """Tool description.

    Args:
        param: Parameter description
    """
    # Your implementation
    return result

# Add to appropriate specialist
specialist.tools.append(your_custom_tool)
```

### Modify Guardrails

```python
async def custom_guardrail(ctx, agent, input_data):
    """Your validation logic."""
    # Check conditions
    is_valid = your_validation_logic(input_data)

    return GuardrailFunctionOutput(
        output_info={"valid": is_valid},
        tripwire_triggered=not is_valid
    )

# Add to agent
agent.input_guardrails.append(InputGuardrail(guardrail_function=custom_guardrail))
```

## Production Considerations

1. **Database Integration**: Replace simulated data with real database queries
2. **Ticketing System**: Connect to actual ticketing/CRM system
3. **Monitoring**: Add logging and metrics tracking
4. **Rate Limiting**: Implement request rate limits
5. **Session Management**: Use Redis for distributed sessions
6. **Error Recovery**: Add retry logic and fallback strategies
7. **Authentication**: Add user authentication and authorization
8. **Caching**: Cache frequent queries and responses

## Next Steps

- Integrate with your actual backend systems
- Add more specialized agents for your domain
- Implement streaming responses for better UX
- Add output guardrails for content filtering
- Set up tracing dashboard for monitoring
- Deploy with proper error handling and logging

## Learn More

See the OpenAI Agents SDK skill documentation for:
- Advanced multi-agent patterns
- Guardrail best practices
- Session management strategies
- Production deployment guides
