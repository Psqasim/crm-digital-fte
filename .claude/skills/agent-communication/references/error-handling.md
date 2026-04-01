# Error Handling in Multi-Agent Systems

## Error Categories

| Category | Scope | Recovery | Example |
|----------|-------|----------|---------|
| **Validation** | Input | Client fixes | Empty title |
| **NotFound** | Data | Client retry | Task not found |
| **Routing** | Orchestrator | Config fix | Unknown action |
| **Agent** | Processing | Depends | Storage failure |
| **System** | Infrastructure | Ops | Network down |

## Exception Hierarchy

```python
from typing import Any

class AgentError(Exception):
    """Base exception for all agent errors."""

    def __init__(
        self,
        message: str,
        code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code or self.__class__.__name__.upper()
        self.details = details or {}

    def to_response(self, correlation_id: str | None = None) -> AgentResponse:
        """Convert exception to AgentResponse."""
        return AgentResponse.error(
            code=self.code,
            message=str(self),
            correlation_id=correlation_id,
        )


class ValidationError(AgentError):
    """Invalid input data."""

    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(message, code="VALIDATION_ERROR")
        if field:
            self.details["field"] = field


class NotFoundError(AgentError):
    """Requested resource not found."""

    def __init__(self, resource_type: str, resource_id: str) -> None:
        super().__init__(
            f"{resource_type} not found: {resource_id}",
            code="NOT_FOUND",
        )
        self.details["resource_type"] = resource_type
        self.details["resource_id"] = resource_id


class RoutingError(AgentError):
    """Failed to route message to agent."""

    def __init__(self, action: str) -> None:
        super().__init__(
            f"No agent registered for action: {action}",
            code="ROUTING_ERROR",
        )
        self.details["action"] = action


class StorageError(AgentError):
    """Storage operation failed."""

    def __init__(self, operation: str, message: str) -> None:
        super().__init__(message, code="STORAGE_ERROR")
        self.details["operation"] = operation


class AgentNotReadyError(AgentError):
    """Agent not in ready state."""

    def __init__(self, agent_name: str, status: str) -> None:
        super().__init__(
            f"Agent {agent_name} is {status}",
            code="AGENT_NOT_READY",
        )
        self.details["agent"] = agent_name
        self.details["status"] = status
```

## Error Handling Patterns

### Pattern 1: Catch at Boundary

```python
class TaskManagerAgent:
    """Agent with boundary error handling."""

    def handle_message(self, message: AgentMessage) -> AgentResponse:
        """All errors caught here and converted to responses."""
        try:
            return self._process_message(message)
        except ValidationError as e:
            return e.to_response(message.correlation_id)
        except NotFoundError as e:
            return e.to_response(message.correlation_id)
        except AgentError as e:
            return e.to_response(message.correlation_id)
        except Exception as e:
            # Unexpected errors - log and return generic response
            logger.exception(f"Unexpected error: {e}")
            return AgentResponse.error(
                "INTERNAL_ERROR",
                "An unexpected error occurred",
                correlation_id=message.correlation_id,
            )

    def _process_message(self, message: AgentMessage) -> AgentResponse:
        """Internal processing - can raise exceptions."""
        if message.action == "task_add":
            return self._add_task(message.payload)
        elif message.action == "task_get":
            return self._get_task(message.payload)
        # ...
        raise ValidationError(f"Unknown action: {message.action}")
```

### Pattern 2: Error Propagation

```python
class OrchestratorAgent:
    """Orchestrator that propagates errors from child agents."""

    def handle_message(self, message: AgentMessage) -> AgentResponse:
        try:
            agent = self._resolve_agent(message.action)
            response = agent.handle_message(message)

            # Enrich response with routing info
            if not response.success:
                return self._enrich_error(response, message)

            return response

        except RoutingError as e:
            return e.to_response(message.correlation_id)

    def _enrich_error(
        self,
        response: AgentResponse,
        message: AgentMessage,
    ) -> AgentResponse:
        """Add context to error responses."""
        return response.model_copy(update={
            "correlation_id": message.correlation_id,
            # Preserve original error, add routing context
        })
```

### Pattern 3: Retry with Backoff

```python
import asyncio
from typing import TypeVar

T = TypeVar("T")

async def retry_with_backoff(
    func: Callable[[], T],
    max_retries: int = 3,
    base_delay: float = 0.1,
    max_delay: float = 10.0,
    retryable_errors: tuple[type[Exception], ...] = (StorageError,),
) -> T:
    """Retry function with exponential backoff."""
    last_error: Exception | None = None

    for attempt in range(max_retries):
        try:
            return func()
        except retryable_errors as e:
            last_error = e
            if attempt < max_retries - 1:
                delay = min(base_delay * (2 ** attempt), max_delay)
                logger.warning(f"Retry {attempt + 1}/{max_retries} after {delay}s: {e}")
                await asyncio.sleep(delay)

    raise last_error

# Usage in agent
async def _save_with_retry(self, task: Task) -> None:
    await retry_with_backoff(
        lambda: self._storage.save(task),
        max_retries=3,
        retryable_errors=(StorageError,),
    )
```

## Error Response Structure

### Standard Error Response

```python
# Error responses always include:
AgentResponse(
    success=False,
    data=None,
    error_code="NOT_FOUND",           # Machine-readable code
    error_message="Task not found: abc123",  # Human-readable
    correlation_id="req-456",         # For tracing
    source_agent="task_manager",      # Origin of error
)
```

### Error with Details

```python
class DetailedAgentResponse(AgentResponse):
    """Extended response with error details."""
    error_details: dict[str, Any] | None = None

# Usage
return DetailedAgentResponse(
    success=False,
    error_code="VALIDATION_ERROR",
    error_message="Invalid task data",
    error_details={
        "field": "title",
        "constraint": "min_length",
        "value": "",
        "required": 1,
    },
)
```

## Error Logging

### Structured Error Logging

```python
import structlog

logger = structlog.get_logger()

def handle_message(self, message: AgentMessage) -> AgentResponse:
    log = logger.bind(
        action=message.action,
        correlation_id=message.correlation_id,
        source_agent=message.source_agent,
    )

    try:
        result = self._process(message)
        log.info("message_processed", success=True)
        return result
    except ValidationError as e:
        log.warning("validation_error", error=str(e), **e.details)
        return e.to_response(message.correlation_id)
    except NotFoundError as e:
        log.info("not_found", **e.details)
        return e.to_response(message.correlation_id)
    except Exception as e:
        log.exception("unexpected_error", error=str(e))
        return AgentResponse.error(
            "INTERNAL_ERROR",
            "Internal error occurred",
            correlation_id=message.correlation_id,
        )
```

## Circuit Breaker Pattern

```python
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum, auto

class CircuitState(Enum):
    CLOSED = auto()    # Normal operation
    OPEN = auto()      # Failing, reject requests
    HALF_OPEN = auto() # Testing recovery

@dataclass
class CircuitBreaker:
    """Prevent cascading failures."""

    failure_threshold: int = 5
    recovery_timeout: timedelta = timedelta(seconds=30)

    _failures: int = 0
    _state: CircuitState = CircuitState.CLOSED
    _last_failure: datetime | None = None

    def call(self, func: Callable[[], T]) -> T:
        """Execute function with circuit breaker protection."""
        if self._state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._state = CircuitState.HALF_OPEN
            else:
                raise AgentNotReadyError("circuit_breaker", "OPEN")

        try:
            result = func()
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        if not self._last_failure:
            return True
        return datetime.utcnow() - self._last_failure > self.recovery_timeout

    def _on_success(self) -> None:
        self._failures = 0
        self._state = CircuitState.CLOSED

    def _on_failure(self) -> None:
        self._failures += 1
        self._last_failure = datetime.utcnow()
        if self._failures >= self.failure_threshold:
            self._state = CircuitState.OPEN

# Usage
class StorageAgent:
    def __init__(self) -> None:
        self._circuit = CircuitBreaker(failure_threshold=3)

    def handle_message(self, message: AgentMessage) -> AgentResponse:
        try:
            return self._circuit.call(lambda: self._process(message))
        except AgentNotReadyError as e:
            return e.to_response(message.correlation_id)
```

## Best Practices

### 1. Never Expose Internal Details

```python
# BAD: Exposes stack trace
return AgentResponse.error("ERROR", str(traceback.format_exc()))

# GOOD: Generic message, details logged
logger.exception("Database error")
return AgentResponse.error("STORAGE_ERROR", "Failed to save task")
```

### 2. Use Specific Error Codes

```python
# BAD: Generic
return AgentResponse.error("ERROR", "Something went wrong")

# GOOD: Specific and actionable
return AgentResponse.error("VALIDATION_ERROR", "Title exceeds 200 characters")
```

### 3. Include Correlation ID Always

```python
# Every error response should be traceable
return AgentResponse.error(
    code="NOT_FOUND",
    message="Task not found",
    correlation_id=message.correlation_id,  # Always include
)
```
