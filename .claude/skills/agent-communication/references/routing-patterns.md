# Routing Patterns

## Overview

Routing determines which agent handles each message based on action type, content, or other criteria.

| Pattern | Use Case | Complexity |
|---------|----------|------------|
| **Prefix Routing** | Static action-to-agent mapping | Simple |
| **Registry Pattern** | Dynamic agent registration | Medium |
| **Content-Based** | Route by payload content | Medium |
| **Priority Queue** | Ordered processing | Complex |

## Prefix Routing (Recommended for Phase I)

### Basic Implementation

```python
from typing import Protocol

class BaseAgent(Protocol):
    def handle_message(self, message: AgentMessage) -> AgentResponse: ...

class OrchestratorAgent:
    """Routes messages based on action prefix."""

    def __init__(self) -> None:
        self._agents: dict[str, BaseAgent] = {}
        self._routes: dict[str, str] = {}

    def register_agent(
        self,
        name: str,
        agent: BaseAgent,
        prefixes: list[str],
    ) -> None:
        """Register agent with its action prefixes."""
        self._agents[name] = agent
        for prefix in prefixes:
            self._routes[prefix] = name

    def handle_message(self, message: AgentMessage) -> AgentResponse:
        """Route message to appropriate agent."""
        agent_name = self._resolve_route(message.action)

        if not agent_name:
            return AgentResponse.error(
                "ROUTING_ERROR",
                f"No agent registered for action: {message.action}",
                correlation_id=message.correlation_id,
            )

        agent = self._agents.get(agent_name)
        if not agent:
            return AgentResponse.error(
                "AGENT_NOT_FOUND",
                f"Agent not found: {agent_name}",
                correlation_id=message.correlation_id,
            )

        response = agent.handle_message(message)
        return response

    def _resolve_route(self, action: str) -> str | None:
        """Find agent for action using longest prefix match."""
        # Sort by prefix length (longest first) for specificity
        for prefix in sorted(self._routes.keys(), key=len, reverse=True):
            if action.startswith(prefix):
                return self._routes[prefix]
        return None
```

### Usage

```python
orchestrator = OrchestratorAgent()

# Register agents with prefixes
orchestrator.register_agent(
    "task_manager",
    TaskManagerAgent(storage=storage),
    prefixes=["task_"],
)
orchestrator.register_agent(
    "storage",
    StorageAgent(backend=backend),
    prefixes=["storage_"],
)
orchestrator.register_agent(
    "ui",
    UIControllerAgent(adapter=console),
    prefixes=["ui_"],
)

# Route messages
response = orchestrator.handle_message(
    AgentMessage(action="task_add", payload={"title": "Test"})
)
# Routed to task_manager
```

## Registry Pattern

### Agent Registry

```python
from dataclasses import dataclass
from enum import Enum, auto

class AgentStatus(Enum):
    INITIALIZING = auto()
    READY = auto()
    BUSY = auto()
    SHUTTING_DOWN = auto()
    STOPPED = auto()

@dataclass
class AgentInfo:
    """Metadata about registered agent."""
    name: str
    agent: BaseAgent
    prefixes: list[str]
    status: AgentStatus = AgentStatus.INITIALIZING
    version: str = "1.0.0"
    capabilities: list[str] = None

    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []

class AgentRegistry:
    """Central registry for agent management."""

    def __init__(self) -> None:
        self._agents: dict[str, AgentInfo] = {}
        self._prefix_map: dict[str, str] = {}

    def register(self, info: AgentInfo) -> None:
        """Register agent with metadata."""
        if info.name in self._agents:
            raise ValueError(f"Agent already registered: {info.name}")

        self._agents[info.name] = info
        for prefix in info.prefixes:
            if prefix in self._prefix_map:
                raise ValueError(f"Prefix conflict: {prefix}")
            self._prefix_map[prefix] = info.name

        info.status = AgentStatus.READY

    def unregister(self, name: str) -> None:
        """Remove agent from registry."""
        info = self._agents.pop(name, None)
        if info:
            for prefix in info.prefixes:
                self._prefix_map.pop(prefix, None)

    def get_agent(self, name: str) -> BaseAgent | None:
        """Get agent by name."""
        info = self._agents.get(name)
        return info.agent if info else None

    def resolve_action(self, action: str) -> AgentInfo | None:
        """Find agent info for action."""
        for prefix in sorted(self._prefix_map.keys(), key=len, reverse=True):
            if action.startswith(prefix):
                name = self._prefix_map[prefix]
                return self._agents.get(name)
        return None

    def list_agents(self) -> list[AgentInfo]:
        """List all registered agents."""
        return list(self._agents.values())

    def get_status(self, name: str) -> AgentStatus | None:
        """Get agent status."""
        info = self._agents.get(name)
        return info.status if info else None
```

### Orchestrator with Registry

```python
class OrchestratorAgent:
    """Orchestrator using registry pattern."""

    def __init__(self, registry: AgentRegistry) -> None:
        self._registry = registry

    def handle_message(self, message: AgentMessage) -> AgentResponse:
        info = self._registry.resolve_action(message.action)

        if not info:
            return AgentResponse.error(
                "ROUTING_ERROR",
                f"No agent for action: {message.action}",
            )

        if info.status != AgentStatus.READY:
            return AgentResponse.error(
                "AGENT_NOT_READY",
                f"Agent {info.name} status: {info.status.name}",
            )

        return info.agent.handle_message(message)
```

## Content-Based Routing

### Route by Payload Content

```python
from typing import Callable

class ContentRouter:
    """Routes based on message content."""

    def __init__(self) -> None:
        self._rules: list[tuple[Callable[[AgentMessage], bool], str]] = []
        self._agents: dict[str, BaseAgent] = {}

    def add_rule(
        self,
        condition: Callable[[AgentMessage], bool],
        agent_name: str,
    ) -> None:
        """Add routing rule with condition."""
        self._rules.append((condition, agent_name))

    def register_agent(self, name: str, agent: BaseAgent) -> None:
        self._agents[name] = agent

    def route(self, message: AgentMessage) -> AgentResponse:
        for condition, agent_name in self._rules:
            if condition(message):
                agent = self._agents.get(agent_name)
                if agent:
                    return agent.handle_message(message)

        return AgentResponse.error("ROUTING_ERROR", "No matching rule")

# Usage
router = ContentRouter()
router.register_agent("high_priority", HighPriorityAgent())
router.register_agent("default", DefaultAgent())

# Route high-priority messages to dedicated agent
router.add_rule(
    lambda m: m.priority == Priority.CRITICAL,
    "high_priority",
)
router.add_rule(
    lambda m: True,  # Default catch-all
    "default",
)
```

## Routing Table Configuration

### Declarative Routing

```python
from pydantic import BaseModel

class RouteConfig(BaseModel):
    """Configuration for a single route."""
    prefix: str
    agent: str
    enabled: bool = True
    rate_limit: int | None = None  # requests per second

class RoutingConfig(BaseModel):
    """Complete routing configuration."""
    routes: list[RouteConfig]
    default_agent: str | None = None

# Load from YAML/JSON
ROUTING_CONFIG = """
routes:
  - prefix: "task_"
    agent: "task_manager"
    enabled: true
  - prefix: "storage_"
    agent: "storage"
    enabled: true
  - prefix: "ui_"
    agent: "ui_controller"
    enabled: true
default_agent: null
"""

config = RoutingConfig.model_validate(yaml.safe_load(ROUTING_CONFIG))
```

## Middleware Pattern

### Pre/Post Processing

```python
from typing import Callable
from functools import wraps

Middleware = Callable[[AgentMessage, Callable], AgentResponse]

class MiddlewareOrchestrator:
    """Orchestrator with middleware support."""

    def __init__(self) -> None:
        self._agents: dict[str, BaseAgent] = {}
        self._middleware: list[Middleware] = []

    def use(self, middleware: Middleware) -> None:
        """Add middleware to pipeline."""
        self._middleware.append(middleware)

    def handle_message(self, message: AgentMessage) -> AgentResponse:
        def dispatch(msg: AgentMessage) -> AgentResponse:
            agent = self._resolve_agent(msg.action)
            return agent.handle_message(msg)

        # Build middleware chain
        handler = dispatch
        for mw in reversed(self._middleware):
            handler = self._wrap_middleware(mw, handler)

        return handler(message)

    def _wrap_middleware(
        self,
        mw: Middleware,
        next_handler: Callable,
    ) -> Callable:
        return lambda msg: mw(msg, next_handler)

# Example middleware
def logging_middleware(
    message: AgentMessage,
    next_handler: Callable,
) -> AgentResponse:
    """Log all messages."""
    logger.info(f"Handling: {message.action}")
    response = next_handler(message)
    logger.info(f"Response: {response.success}")
    return response

def timing_middleware(
    message: AgentMessage,
    next_handler: Callable,
) -> AgentResponse:
    """Track processing time."""
    start = time.perf_counter()
    response = next_handler(message)
    elapsed = (time.perf_counter() - start) * 1000
    return response.model_copy(update={"processing_time_ms": elapsed})

# Usage
orchestrator = MiddlewareOrchestrator()
orchestrator.use(logging_middleware)
orchestrator.use(timing_middleware)
```

## Best Practices

### 1. Fail Fast on Unknown Actions

```python
def handle_message(self, message: AgentMessage) -> AgentResponse:
    if not self._can_route(message.action):
        return AgentResponse.error(
            "UNKNOWN_ACTION",
            f"Action not recognized: {message.action}",
        )
    # Continue processing
```

### 2. Use Longest Prefix Match

```python
# More specific routes take precedence
routes = {
    "task_batch_": "batch_processor",  # More specific
    "task_": "task_manager",           # Less specific
}

# "task_batch_add" → batch_processor
# "task_add" → task_manager
```

### 3. Include Route Info in Response

```python
response = agent.handle_message(message)
return response.model_copy(update={
    "source_agent": agent_name,
    "correlation_id": message.correlation_id,
})
```
