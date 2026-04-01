# Advanced Topics

Comprehensive guide to tracing, hooks, streaming, custom configurations, and production-ready patterns.

## Table of Contents
- Tracing and Observability
- RunHooks and Lifecycle Events
- RunConfig and Customization
- Usage Tracking
- Error Handling Patterns
- Production Best Practices

## Tracing and Observability

Tracing is built-in and enabled by default, capturing a comprehensive record of all agent execution events.

### Default Tracing

```python
from agents import Agent, Runner
import asyncio

agent = Agent(
    name="Assistant",
    instructions="Be helpful."
)

async def main():
    # Tracing automatically captures:
    # - LLM generations
    # - Tool calls
    # - Handoffs
    # - Guardrails
    # - Custom events
    result = await Runner.run(agent, "Hello!")

    # View traces in OpenAI Traces dashboard
    print(result.final_output)

asyncio.run(main())
```

### Adding Trace Context

Enrich traces with metadata:

```python
from agents.tracing.traces import trace

async def process_request(user_id: str, query: str):
    """Process user request with tracing context."""

    with trace(
        workflow_name="Customer Support",
        group_id=f"user_{user_id}",
        metadata={
            "user_id": user_id,
            "query_type": "support",
            "environment": "production"
        }
    ) as t:
        result = await Runner.run(support_agent, query)
        return result.final_output

# All agent activity is grouped and tagged
await process_request("user_123", "Help with my account")
```

### Manual Trace Management

```python
from agents.tracing.traces import trace

async def custom_workflow():
    """Workflow with manual trace control."""

    t = trace(
        workflow_name="Data Pipeline",
        trace_id="pipeline_run_456",
        metadata={"pipeline": "etl", "version": "2.1"}
    )

    # Manually start trace
    t.start()

    try:
        # Your workflow
        result = await Runner.run(agent, "Process data")

        # Add custom events
        t.add_event("data_processed", {"records": 1000})

    finally:
        # Manually finish trace
        t.finish()

    return result
```

### Disabling Tracing

Globally disable:

```bash
export OPENAI_AGENTS_DISABLE_TRACING=1
```

Per-run disable:

```python
from agents.run import RunConfig

result = await Runner.run(
    agent,
    user_input,
    run_config=RunConfig(tracing_disabled=True)
)
```

### Custom Trace Events

```python
from agents.tracing.traces import trace

async def traced_workflow():
    with trace("Custom Workflow") as t:
        # Start marker
        t.add_event("workflow_started", {"timestamp": datetime.now().isoformat()})

        # Processing step
        result = await Runner.run(agent, "Analyze data")
        t.add_event("analysis_complete", {"output_length": len(result.final_output)})

        # Another step
        validation_passed = True  # Your validation logic
        t.add_event("validation", {"passed": validation_passed})

        # Completion marker
        t.add_event("workflow_complete", {"success": True})

        return result
```

## RunHooks and Lifecycle Events

Hooks provide callbacks at key points in agent execution.

### Available Hooks

```python
from agents import RunHooks, RunContextWrapper, Agent
from typing import Any

class MyHooks(RunHooks):
    """Custom hooks for agent lifecycle events."""

    async def on_agent_start(
        self,
        context: RunContextWrapper,
        agent: Agent,
        input_data: Any
    ) -> None:
        """Called when agent starts processing."""
        print(f"🟢 Agent '{agent.name}' starting with input: {input_data}")

    async def on_agent_end(
        self,
        context: RunContextWrapper,
        agent: Agent,
        output: Any
    ) -> None:
        """Called when agent finishes."""
        print(f"🔵 Agent '{agent.name}' completed")

        # Access usage metrics
        usage = context.usage
        print(f"   Requests: {usage.requests}")
        print(f"   Total tokens: {usage.total_tokens}")
        print(f"   Prompt tokens: {usage.prompt_tokens}")
        print(f"   Completion tokens: {usage.completion_tokens}")

    async def on_tool_call_start(
        self,
        context: RunContextWrapper,
        agent: Agent,
        tool_name: str,
        tool_arguments: dict
    ) -> None:
        """Called before tool execution."""
        print(f"🔧 Calling tool '{tool_name}' with args: {tool_arguments}")

    async def on_tool_call_end(
        self,
        context: RunContextWrapper,
        agent: Agent,
        tool_name: str,
        tool_output: Any
    ) -> None:
        """Called after tool execution."""
        print(f"✅ Tool '{tool_name}' returned: {tool_output}")

    async def on_handoff(
        self,
        context: RunContextWrapper,
        from_agent: Agent,
        to_agent: Agent
    ) -> None:
        """Called when agent hands off to another."""
        print(f"🔄 Handoff: {from_agent.name} → {to_agent.name}")

# Use hooks
result = await Runner.run(
    agent,
    "Process this request",
    hooks=MyHooks()
)
```

### Logging Hook

```python
import logging

class LoggingHook(RunHooks):
    """Log all agent activities."""

    def __init__(self):
        self.logger = logging.getLogger("agents")
        self.logger.setLevel(logging.INFO)

    async def on_agent_start(self, context, agent, input_data):
        self.logger.info(f"Agent {agent.name} started", extra={
            "agent": agent.name,
            "input_length": len(str(input_data))
        })

    async def on_agent_end(self, context, agent, output):
        self.logger.info(f"Agent {agent.name} completed", extra={
            "agent": agent.name,
            "usage": context.usage.model_dump()
        })

    async def on_tool_call_start(self, context, agent, tool_name, tool_arguments):
        self.logger.debug(f"Tool call: {tool_name}", extra={
            "tool": tool_name,
            "args": tool_arguments
        })

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Use logging hook
result = await Runner.run(agent, "Query", hooks=LoggingHook())
```

### Performance Monitoring Hook

```python
import time
from dataclasses import dataclass, field
from typing import Dict, List

@dataclass
class PerformanceMetrics:
    agent_times: Dict[str, float] = field(default_factory=dict)
    tool_times: Dict[str, List[float]] = field(default_factory=dict)
    total_time: float = 0.0

class PerformanceHook(RunHooks):
    """Monitor performance metrics."""

    def __init__(self):
        self.metrics = PerformanceMetrics()
        self.start_times = {}

    async def on_agent_start(self, context, agent, input_data):
        self.start_times[agent.name] = time.time()

    async def on_agent_end(self, context, agent, output):
        if agent.name in self.start_times:
            duration = time.time() - self.start_times[agent.name]
            self.metrics.agent_times[agent.name] = duration

    async def on_tool_call_start(self, context, agent, tool_name, tool_arguments):
        self.start_times[f"tool:{tool_name}"] = time.time()

    async def on_tool_call_end(self, context, agent, tool_name, tool_output):
        key = f"tool:{tool_name}"
        if key in self.start_times:
            duration = time.time() - self.start_times[key]
            if tool_name not in self.metrics.tool_times:
                self.metrics.tool_times[tool_name] = []
            self.metrics.tool_times[tool_name].append(duration)

    def get_report(self) -> str:
        """Generate performance report."""
        report = ["Performance Report:", ""]

        report.append("Agent Execution Times:")
        for agent_name, duration in self.metrics.agent_times.items():
            report.append(f"  {agent_name}: {duration:.3f}s")

        report.append("\nTool Execution Times:")
        for tool_name, times in self.metrics.tool_times.items():
            avg_time = sum(times) / len(times)
            report.append(f"  {tool_name}: {len(times)} calls, avg {avg_time:.3f}s")

        return "\n".join(report)

# Usage
perf_hook = PerformanceHook()
result = await Runner.run(agent, "Complex query", hooks=perf_hook)
print(perf_hook.get_report())
```

### Cost Tracking Hook

```python
class CostTrackingHook(RunHooks):
    """Track API costs based on usage."""

    # Pricing per 1M tokens (example rates)
    PRICES = {
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    }

    def __init__(self):
        self.total_cost = 0.0
        self.cost_breakdown = {}

    async def on_agent_end(self, context, agent, output):
        usage = context.usage
        model = agent.model or "gpt-4o"

        # Calculate cost
        input_cost = (usage.prompt_tokens / 1_000_000) * self.PRICES[model]["input"]
        output_cost = (usage.completion_tokens / 1_000_000) * self.PRICES[model]["output"]
        agent_cost = input_cost + output_cost

        # Track
        self.total_cost += agent_cost
        self.cost_breakdown[agent.name] = agent_cost

        print(f"💰 {agent.name} cost: ${agent_cost:.4f}")

    def get_total(self) -> float:
        return self.total_cost

# Usage
cost_hook = CostTrackingHook()
result = await Runner.run(agent, "Query", hooks=cost_hook)
print(f"Total cost: ${cost_hook.get_total():.4f}")
```

## RunConfig and Customization

Configure agent execution with RunConfig.

### Basic RunConfig

```python
from agents.run import RunConfig
from agents import ModelSettings

config = RunConfig(
    # Model configuration
    model_settings=ModelSettings(
        temperature=0.8,
        max_tokens=2000
    ),

    # Execution control
    tracing_disabled=False,

    # Additional settings
    # ... (provider-specific options)
)

result = await Runner.run(
    agent,
    user_input,
    run_config=config
)
```

### Per-Run Model Override

```python
# Agent has default settings
agent = Agent(
    name="Agent",
    model_settings=ModelSettings(temperature=0.7)
)

# Override for specific run
result = await Runner.run(
    agent,
    "Complex task requiring more creativity",
    run_config=RunConfig(
        model_settings=ModelSettings(
            temperature=0.95,  # Override
            max_tokens=3000    # Override
        )
    )
)
```

### Combined Configuration

```python
async def configured_run(user_input: str):
    """Run with full configuration."""

    hooks = MyHooks()
    config = RunConfig(
        model_settings=ModelSettings(
            temperature=0.7,
            max_tokens=1500,
            metadata={"run_id": "abc123"}
        ),
        tracing_disabled=False
    )

    result = await Runner.run(
        agent,
        user_input,
        context=my_context,
        session=my_session,
        max_turns=10,
        hooks=hooks,
        run_config=config
    )

    return result.final_output
```

## Usage Tracking

Track token usage and costs.

### Accessing Usage Metrics

```python
result = await Runner.run(agent, "Query")

# Usage available in result
usage = result.usage
print(f"Requests: {usage.requests}")
print(f"Total tokens: {usage.total_tokens}")
print(f"Prompt tokens: {usage.prompt_tokens}")
print(f"Completion tokens: {usage.completion_tokens}")
```

### Usage in Hooks

```python
class UsageHook(RunHooks):
    async def on_agent_end(self, context, agent, output):
        usage = context.usage
        print(f"{agent.name} used {usage.total_tokens} tokens")
```

### Cumulative Usage Tracking

```python
class CumulativeUsageTracker:
    """Track usage across multiple runs."""

    def __init__(self):
        self.total_tokens = 0
        self.total_requests = 0
        self.by_agent = {}

    async def run_and_track(self, agent: Agent, user_input: str):
        """Run agent and track usage."""

        result = await Runner.run(agent, user_input)

        # Update totals
        usage = result.usage
        self.total_tokens += usage.total_tokens
        self.total_requests += usage.requests

        # Track per agent
        if agent.name not in self.by_agent:
            self.by_agent[agent.name] = {"tokens": 0, "requests": 0}

        self.by_agent[agent.name]["tokens"] += usage.total_tokens
        self.by_agent[agent.name]["requests"] += usage.requests

        return result.final_output

    def get_report(self):
        """Get usage summary."""
        return {
            "total_tokens": self.total_tokens,
            "total_requests": self.total_requests,
            "by_agent": self.by_agent
        }

# Usage
tracker = CumulativeUsageTracker()
await tracker.run_and_track(agent1, "Query 1")
await tracker.run_and_track(agent2, "Query 2")
print(tracker.get_report())
```

## Error Handling Patterns

Robust error handling for production systems.

### Comprehensive Error Handler

```python
from agents.exceptions import (
    MaxTurnsExceeded,
    InputGuardrailTripwireTriggered,
    OutputGuardrailTripwireTriggered,
    AgentsException
)

async def safe_agent_run(
    agent: Agent,
    user_input: str,
    max_retries: int = 3
) -> dict:
    """Run agent with comprehensive error handling."""

    for attempt in range(max_retries):
        try:
            result = await Runner.run(
                agent,
                user_input,
                max_turns=10
            )

            return {
                "success": True,
                "output": result.final_output,
                "usage": result.usage.model_dump(),
                "attempts": attempt + 1
            }

        except InputGuardrailTripwireTriggered as e:
            # Input blocked - no retry
            return {
                "success": False,
                "error": "input_blocked",
                "details": e.guardrail_result.output.output_info,
                "retryable": False
            }

        except OutputGuardrailTripwireTriggered as e:
            # Output blocked - could retry with different prompt
            if attempt < max_retries - 1:
                print(f"Attempt {attempt + 1} failed guardrail, retrying...")
                user_input += "\n[Previous response had issues. Please revise.]"
                continue
            else:
                return {
                    "success": False,
                    "error": "output_blocked",
                    "details": e.guardrail_result.output.output_info,
                    "retryable": True,
                    "attempts": attempt + 1
                }

        except MaxTurnsExceeded as e:
            # Too complex - could try with simpler prompt
            return {
                "success": False,
                "error": "max_turns_exceeded",
                "details": "Task too complex or infinite loop detected",
                "retryable": True,
                "attempts": attempt + 1
            }

        except AgentsException as e:
            # Other SDK exceptions
            return {
                "success": False,
                "error": "agent_error",
                "details": str(e),
                "retryable": False
            }

        except Exception as e:
            # Unexpected errors
            return {
                "success": False,
                "error": "unexpected",
                "details": str(e),
                "retryable": False
            }

    return {
        "success": False,
        "error": "max_retries_exceeded",
        "attempts": max_retries
    }
```

### Timeout Handling

```python
import asyncio

async def run_with_timeout(
    agent: Agent,
    user_input: str,
    timeout_seconds: int = 30
):
    """Run agent with timeout."""

    try:
        result = await asyncio.wait_for(
            Runner.run(agent, user_input),
            timeout=timeout_seconds
        )
        return result.final_output

    except asyncio.TimeoutError:
        print(f"⏱️ Agent execution timed out after {timeout_seconds}s")
        return "Request timed out. Please try a simpler query."
```

## Production Best Practices

### 1. Configuration Management

```python
from dataclasses import dataclass
import os

@dataclass
class AgentConfig:
    """Production agent configuration."""

    openai_api_key: str
    model: str = "gpt-4o"
    max_turns: int = 10
    temperature: float = 0.7
    max_tokens: int = 2000
    tracing_enabled: bool = True
    session_db_path: str = "sessions.db"

    @classmethod
    def from_env(cls):
        """Load from environment variables."""
        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            model=os.getenv("AGENT_MODEL", "gpt-4o"),
            max_turns=int(os.getenv("AGENT_MAX_TURNS", "10")),
            temperature=float(os.getenv("AGENT_TEMPERATURE", "0.7")),
            tracing_enabled=os.getenv("TRACING_ENABLED", "true").lower() == "true"
        )

# Usage
config = AgentConfig.from_env()

agent = Agent(
    name="Production Agent",
    model=config.model,
    model_settings=ModelSettings(
        temperature=config.temperature,
        max_tokens=config.max_tokens
    )
)
```

### 2. Health Checks

```python
async def health_check() -> dict:
    """Verify agent system health."""

    try:
        test_agent = Agent(
            name="Health Check",
            instructions="Respond with 'OK'",
            model_settings=ModelSettings(max_tokens=10)
        )

        result = await asyncio.wait_for(
            Runner.run(test_agent, "Health check"),
            timeout=5.0
        )

        return {
            "status": "healthy",
            "latency_ms": 0,  # Measure actual latency
            "model": test_agent.model
        }

    except asyncio.TimeoutError:
        return {"status": "timeout", "error": "Health check timed out"}

    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

### 3. Rate Limiting

```python
from asyncio import Semaphore

class RateLimitedRunner:
    """Limit concurrent agent executions."""

    def __init__(self, max_concurrent: int = 10):
        self.semaphore = Semaphore(max_concurrent)

    async def run(self, agent: Agent, user_input: str, **kwargs):
        """Run with rate limiting."""
        async with self.semaphore:
            return await Runner.run(agent, user_input, **kwargs)

# Usage
runner = RateLimitedRunner(max_concurrent=5)
results = await asyncio.gather(*[
    runner.run(agent, f"Query {i}")
    for i in range(100)  # Only 5 concurrent
])
```

### 4. Graceful Degradation

```python
async def resilient_agent_system(user_input: str):
    """Multi-tier fallback system."""

    # Tier 1: Primary agent (advanced)
    try:
        primary = Agent(name="Primary", model="gpt-4o")
        result = await asyncio.wait_for(
            Runner.run(primary, user_input, max_turns=10),
            timeout=15.0
        )
        return result.final_output

    except (asyncio.TimeoutError, MaxTurnsExceeded):
        print("Primary agent failed, trying fallback...")

    # Tier 2: Fallback agent (faster)
    try:
        fallback = Agent(name="Fallback", model="gpt-4o-mini")
        result = await asyncio.wait_for(
            Runner.run(fallback, user_input, max_turns=5),
            timeout=10.0
        )
        return result.final_output

    except Exception:
        print("All agents failed, returning error message...")

    # Tier 3: Error response
    return "Service temporarily unavailable. Please try again later."
```

### 5. Monitoring and Alerting

```python
import logging
from datetime import datetime

class MonitoringHook(RunHooks):
    """Production monitoring."""

    def __init__(self, alert_threshold_seconds: float = 10.0):
        self.alert_threshold = alert_threshold_seconds
        self.logger = logging.getLogger("agent_monitoring")
        self.start_time = None

    async def on_agent_start(self, context, agent, input_data):
        self.start_time = datetime.now()

    async def on_agent_end(self, context, agent, output):
        duration = (datetime.now() - self.start_time).total_seconds()

        # Log metrics
        self.logger.info("Agent completed", extra={
            "agent": agent.name,
            "duration_seconds": duration,
            "tokens": context.usage.total_tokens,
            "requests": context.usage.requests
        })

        # Alert on slow responses
        if duration > self.alert_threshold:
            self.logger.warning(f"Slow agent response: {duration:.2f}s", extra={
                "agent": agent.name,
                "duration": duration,
                "threshold": self.alert_threshold
            })

            # In production: send to alerting system
            # await send_alert(f"Agent {agent.name} slow: {duration}s")
```

## Best Practices Summary

1. **Enable tracing** - Essential for debugging and monitoring
2. **Use hooks** - Track performance, costs, and errors
3. **Handle errors gracefully** - Comprehensive exception handling
4. **Set max_turns** - Prevent infinite loops
5. **Implement timeouts** - Protect against hanging requests
6. **Rate limit** - Control concurrent executions
7. **Monitor costs** - Track token usage and API costs
8. **Health checks** - Verify system health regularly
9. **Graceful degradation** - Fallback strategies for failures
10. **Log everything** - Comprehensive logging for troubleshooting
