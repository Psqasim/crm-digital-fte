# Tracing Patterns

## Correlation IDs

### Purpose

Correlation IDs link related messages across agents, enabling:
- Request tracing through the system
- Log aggregation for debugging
- Performance analysis
- Error root cause identification

### Implementation

```python
from uuid import uuid4
from contextvars import ContextVar

# Context variable for correlation ID propagation
correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)

def get_correlation_id() -> str:
    """Get current correlation ID or generate new one."""
    cid = correlation_id_var.get()
    if not cid:
        cid = str(uuid4())
        correlation_id_var.set(cid)
    return cid

def set_correlation_id(cid: str) -> None:
    """Set correlation ID for current context."""
    correlation_id_var.set(cid)

# Usage in message handling
class OrchestratorAgent:
    def handle_message(self, message: AgentMessage) -> AgentResponse:
        # Use existing correlation ID or generate new one
        cid = message.correlation_id or str(uuid4())
        set_correlation_id(cid)

        # Ensure message has correlation ID
        if not message.correlation_id:
            message = message.with_correlation(cid)

        response = self._route_message(message)

        # Response includes same correlation ID
        return response.model_copy(update={"correlation_id": cid})
```

### Correlation ID Propagation

```python
class AgentMessage(BaseModel):
    """Message with correlation ID support."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    correlation_id: str | None = None
    # ...

    def with_correlation(self, correlation_id: str) -> "AgentMessage":
        """Create copy with correlation ID."""
        return self.model_copy(update={"correlation_id": correlation_id})

    @classmethod
    def child_of(cls, parent: "AgentMessage", **kwargs) -> "AgentMessage":
        """Create child message inheriting correlation ID."""
        return cls(
            correlation_id=parent.correlation_id,
            **kwargs,
        )

# Usage: Creating related messages
original = AgentMessage(action="task_add", payload={"title": "Test"})
original = original.with_correlation(str(uuid4()))

# Child messages inherit correlation
storage_msg = AgentMessage.child_of(
    original,
    action="storage_save",
    payload={"entity": task.model_dump()},
)
# storage_msg.correlation_id == original.correlation_id
```

## Structured Logging

### Setup with structlog

```python
import structlog
from typing import Any

def configure_logging() -> None:
    """Configure structured logging."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )

logger = structlog.get_logger()
```

### Logging with Correlation

```python
class TaskManagerAgent:
    def __init__(self) -> None:
        self._log = structlog.get_logger().bind(agent="task_manager")

    def handle_message(self, message: AgentMessage) -> AgentResponse:
        # Bind correlation ID to all logs in this context
        log = self._log.bind(
            correlation_id=message.correlation_id,
            action=message.action,
            message_id=message.id,
        )

        log.info("message_received")

        try:
            result = self._process(message)
            log.info("message_processed", success=True)
            return result
        except Exception as e:
            log.error("message_failed", error=str(e), exc_info=True)
            raise
```

### Log Output

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "info",
  "event": "message_received",
  "agent": "task_manager",
  "correlation_id": "abc-123-def",
  "action": "task_add",
  "message_id": "msg-456"
}
{
  "timestamp": "2024-01-15T10:30:45.456Z",
  "level": "info",
  "event": "message_processed",
  "agent": "task_manager",
  "correlation_id": "abc-123-def",
  "action": "task_add",
  "message_id": "msg-456",
  "success": true
}
```

## Distributed Tracing

### Span Model

```python
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

class SpanStatus(Enum):
    OK = "ok"
    ERROR = "error"

@dataclass
class Span:
    """Represents a unit of work in distributed tracing."""

    trace_id: str  # Same as correlation_id
    span_id: str = field(default_factory=lambda: str(uuid4())[:8])
    parent_span_id: str | None = None
    operation: str = ""
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: datetime | None = None
    status: SpanStatus = SpanStatus.OK
    tags: dict[str, str] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)

    def finish(self, status: SpanStatus = SpanStatus.OK) -> None:
        self.end_time = datetime.utcnow()
        self.status = status

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        self.events.append({
            "name": name,
            "timestamp": datetime.utcnow().isoformat(),
            "attributes": attributes or {},
        })

    @property
    def duration_ms(self) -> float | None:
        if not self.end_time:
            return None
        return (self.end_time - self.start_time).total_seconds() * 1000
```

### Tracer Implementation

```python
from contextlib import contextmanager
from contextvars import ContextVar

current_span: ContextVar[Span | None] = ContextVar("current_span", default=None)

class Tracer:
    """Simple tracer for distributed tracing."""

    def __init__(self, service_name: str) -> None:
        self.service_name = service_name
        self._spans: list[Span] = []

    @contextmanager
    def span(self, operation: str, tags: dict[str, str] | None = None):
        """Create a new span context."""
        parent = current_span.get()

        span = Span(
            trace_id=get_correlation_id(),
            parent_span_id=parent.span_id if parent else None,
            operation=operation,
            tags={
                "service": self.service_name,
                **(tags or {}),
            },
        )

        token = current_span.set(span)
        try:
            yield span
            span.finish(SpanStatus.OK)
        except Exception as e:
            span.status = SpanStatus.ERROR
            span.tags["error"] = str(e)
            span.finish(SpanStatus.ERROR)
            raise
        finally:
            self._spans.append(span)
            current_span.reset(token)

# Usage
tracer = Tracer("task-manager")

def handle_message(self, message: AgentMessage) -> AgentResponse:
    with tracer.span("handle_message", tags={"action": message.action}) as span:
        span.add_event("validation_start")
        self._validate(message)
        span.add_event("validation_complete")

        with tracer.span("process_action") as child_span:
            result = self._process(message)

        return result
```

## Request Tracing

### Full Request Trace

```python
@dataclass
class RequestTrace:
    """Complete trace of a request through the system."""

    correlation_id: str
    started_at: datetime
    completed_at: datetime | None = None
    status: str = "in_progress"
    path: list[str] = field(default_factory=list)  # Agent names visited
    spans: list[Span] = field(default_factory=list)
    error: str | None = None

    def add_hop(self, agent_name: str) -> None:
        self.path.append(agent_name)

    def complete(self, success: bool, error: str | None = None) -> None:
        self.completed_at = datetime.utcnow()
        self.status = "success" if success else "error"
        self.error = error

    @property
    def duration_ms(self) -> float | None:
        if not self.completed_at:
            return None
        return (self.completed_at - self.started_at).total_seconds() * 1000

class RequestTracer:
    """Tracks requests through the system."""

    def __init__(self) -> None:
        self._traces: dict[str, RequestTrace] = {}

    def start_trace(self, correlation_id: str) -> RequestTrace:
        trace = RequestTrace(
            correlation_id=correlation_id,
            started_at=datetime.utcnow(),
        )
        self._traces[correlation_id] = trace
        return trace

    def get_trace(self, correlation_id: str) -> RequestTrace | None:
        return self._traces.get(correlation_id)

    def complete_trace(
        self,
        correlation_id: str,
        success: bool,
        error: str | None = None,
    ) -> None:
        trace = self._traces.get(correlation_id)
        if trace:
            trace.complete(success, error)

# Usage in orchestrator
class TracingOrchestrator:
    def __init__(self, tracer: RequestTracer) -> None:
        self._tracer = tracer

    def handle_message(self, message: AgentMessage) -> AgentResponse:
        cid = message.correlation_id or str(uuid4())
        trace = self._tracer.start_trace(cid)
        trace.add_hop("orchestrator")

        try:
            agent = self._resolve_agent(message.action)
            trace.add_hop(agent.name)

            response = agent.handle_message(message)

            self._tracer.complete_trace(cid, response.success)
            return response
        except Exception as e:
            self._tracer.complete_trace(cid, False, str(e))
            raise
```

## Observability Integration

### Metrics Collection

```python
from dataclasses import dataclass
from collections import defaultdict
import time

@dataclass
class Metrics:
    """Simple metrics collector."""

    request_count: int = 0
    error_count: int = 0
    total_duration_ms: float = 0.0
    durations_by_action: dict[str, list[float]] = field(
        default_factory=lambda: defaultdict(list)
    )

    def record_request(self, action: str, duration_ms: float, success: bool) -> None:
        self.request_count += 1
        self.total_duration_ms += duration_ms
        self.durations_by_action[action].append(duration_ms)
        if not success:
            self.error_count += 1

    def get_p95_latency(self, action: str) -> float | None:
        durations = self.durations_by_action.get(action, [])
        if not durations:
            return None
        sorted_durations = sorted(durations)
        idx = int(len(sorted_durations) * 0.95)
        return sorted_durations[idx]

# Middleware for metrics
def metrics_middleware(metrics: Metrics):
    def middleware(message: AgentMessage, next_handler):
        start = time.perf_counter()
        try:
            response = next_handler(message)
            duration = (time.perf_counter() - start) * 1000
            metrics.record_request(message.action, duration, response.success)
            return response
        except Exception:
            duration = (time.perf_counter() - start) * 1000
            metrics.record_request(message.action, duration, False)
            raise
    return middleware
```

### Health Check with Trace Info

```python
@dataclass
class HealthStatus:
    """System health with trace statistics."""

    healthy: bool
    agents: dict[str, str]  # agent -> status
    recent_traces: int
    error_rate: float
    avg_latency_ms: float

def get_health_status(
    agents: dict[str, BaseAgent],
    tracer: RequestTracer,
    metrics: Metrics,
) -> HealthStatus:
    agent_status = {
        name: "healthy" if agent.is_running else "unhealthy"
        for name, agent in agents.items()
    }

    error_rate = (
        metrics.error_count / metrics.request_count
        if metrics.request_count > 0
        else 0.0
    )

    avg_latency = (
        metrics.total_duration_ms / metrics.request_count
        if metrics.request_count > 0
        else 0.0
    )

    return HealthStatus(
        healthy=all(s == "healthy" for s in agent_status.values()),
        agents=agent_status,
        recent_traces=len(tracer._traces),
        error_rate=error_rate,
        avg_latency_ms=avg_latency,
    )
```

## Best Practices

### 1. Generate Correlation ID at Entry Point

```python
# At system boundary (API, CLI, etc.)
def handle_user_request(request: UserRequest) -> Response:
    correlation_id = str(uuid4())
    message = AgentMessage(
        action=request.action,
        payload=request.data,
        correlation_id=correlation_id,  # Set at entry
    )
    return orchestrator.handle_message(message)
```

### 2. Include Correlation in All Logs

```python
# Every log statement includes correlation_id
logger.info(
    "task_created",
    correlation_id=message.correlation_id,
    task_id=task.id,
)
```

### 3. Propagate Through All Layers

```python
# Storage layer
async def save(self, entity: Entity, correlation_id: str) -> None:
    logger.debug("saving_entity", correlation_id=correlation_id)
    # ...

# Service layer
async def create_task(self, title: str, correlation_id: str) -> Task:
    task = Task(title=title)
    await self._storage.save(task, correlation_id=correlation_id)
    return task
```
