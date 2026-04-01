# Message Protocol Design

## Core Principles

1. **Immutability**: Messages are never modified after creation
2. **Self-describing**: Messages contain all context needed for processing
3. **Typed**: Strong typing with Pydantic for validation
4. **Traceable**: Every message has unique ID and optional correlation ID

## AgentMessage Design

### Complete Implementation

```python
from pydantic import BaseModel, Field, field_validator
from typing import Any
from uuid import uuid4
from datetime import datetime
from enum import Enum

class Priority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"

class AgentMessage(BaseModel):
    """
    Immutable message sent to an agent.

    Attributes:
        id: Unique message identifier (auto-generated)
        action: Operation to perform (e.g., "task_add", "storage_get")
        payload: Action-specific data
        correlation_id: Links related messages for tracing
        timestamp: Message creation time (UTC)
        source_agent: Originating agent identifier
        priority: Message priority for queue ordering
        ttl_seconds: Time-to-live for message expiration
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    action: str
    payload: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source_agent: str | None = None
    priority: Priority = Priority.NORMAL
    ttl_seconds: int | None = None

    model_config = {"frozen": True}  # Immutable

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Action cannot be empty")
        if not v.replace("_", "").isalnum():
            raise ValueError("Action must be alphanumeric with underscores")
        return v.lower()

    def with_correlation(self, correlation_id: str) -> "AgentMessage":
        """Create copy with correlation ID (maintains immutability)."""
        return self.model_copy(update={"correlation_id": correlation_id})

    def is_expired(self) -> bool:
        """Check if message has exceeded TTL."""
        if self.ttl_seconds is None:
            return False
        age = (datetime.utcnow() - self.timestamp).total_seconds()
        return age > self.ttl_seconds
```

### Action Naming Convention

```python
# Pattern: {domain}_{operation}
# Domain: Identifies target agent/subsystem
# Operation: Specific action to perform

# Task Manager Actions
"task_add"       # Create new task
"task_get"       # Retrieve task by ID
"task_list"      # List tasks with filters
"task_update"    # Modify task fields
"task_delete"    # Remove task
"task_complete"  # Mark task as done

# Storage Actions
"storage_save"   # Persist entity
"storage_get"    # Retrieve by ID
"storage_delete" # Remove entity
"storage_list"   # List all entities
"storage_query"  # Filter entities

# UI Controller Actions
"ui_show_menu"     # Display main menu
"ui_show_tasks"    # Render task list
"ui_get_input"     # Prompt for user input
"ui_show_message"  # Display notification
"ui_confirm"       # Yes/no confirmation
```

## AgentResponse Design

### Complete Implementation

```python
from pydantic import BaseModel, model_validator
from typing import Any, Self

class AgentResponse(BaseModel):
    """
    Response from an agent.

    Invariants:
        - success=True: data is not None, error fields are None
        - success=False: error_code and error_message are not None
    """

    success: bool
    data: dict[str, Any] | None = None
    error_code: str | None = None
    error_message: str | None = None
    correlation_id: str | None = None
    source_agent: str | None = None
    processing_time_ms: float | None = None

    @model_validator(mode="after")
    def validate_response(self) -> Self:
        if self.success:
            if self.error_code or self.error_message:
                raise ValueError("Success response cannot have error fields")
        else:
            if not self.error_code or not self.error_message:
                raise ValueError("Error response must have error_code and error_message")
        return self

    # Factory methods for clean creation
    @classmethod
    def ok(
        cls,
        data: dict[str, Any],
        correlation_id: str | None = None,
        source_agent: str | None = None,
    ) -> "AgentResponse":
        """Create successful response."""
        return cls(
            success=True,
            data=data,
            correlation_id=correlation_id,
            source_agent=source_agent,
        )

    @classmethod
    def error(
        cls,
        code: str,
        message: str,
        correlation_id: str | None = None,
        source_agent: str | None = None,
    ) -> "AgentResponse":
        """Create error response."""
        return cls(
            success=False,
            error_code=code,
            error_message=message,
            correlation_id=correlation_id,
            source_agent=source_agent,
        )

    @classmethod
    def from_exception(
        cls,
        exc: Exception,
        correlation_id: str | None = None,
    ) -> "AgentResponse":
        """Create error response from exception."""
        code = type(exc).__name__.upper()
        return cls.error(code, str(exc), correlation_id)
```

### Standard Error Codes

```python
class ErrorCode:
    """Standard error codes for agent responses."""

    # Validation errors (4xx equivalent)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    INVALID_ACTION = "INVALID_ACTION"

    # Routing errors
    ROUTING_ERROR = "ROUTING_ERROR"
    UNKNOWN_ACTION = "UNKNOWN_ACTION"
    AGENT_NOT_FOUND = "AGENT_NOT_FOUND"

    # Processing errors (5xx equivalent)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    STORAGE_ERROR = "STORAGE_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"

    # State errors
    AGENT_NOT_READY = "AGENT_NOT_READY"
    AGENT_SHUTTING_DOWN = "AGENT_SHUTTING_DOWN"
```

## Payload Schemas

### Type-Safe Payloads with Pydantic

```python
from pydantic import BaseModel

# Define payload schemas for each action
class TaskAddPayload(BaseModel):
    title: str
    description: str | None = None

class TaskGetPayload(BaseModel):
    id: str

class TaskListPayload(BaseModel):
    completed: bool | None = None
    limit: int = 100
    offset: int = 0

class TaskUpdatePayload(BaseModel):
    id: str
    title: str | None = None
    description: str | None = None
    completed: bool | None = None

# Mapping actions to payload schemas
PAYLOAD_SCHEMAS: dict[str, type[BaseModel]] = {
    "task_add": TaskAddPayload,
    "task_get": TaskGetPayload,
    "task_list": TaskListPayload,
    "task_update": TaskUpdatePayload,
}

def validate_payload(message: AgentMessage) -> BaseModel:
    """Validate and parse payload against schema."""
    schema = PAYLOAD_SCHEMAS.get(message.action)
    if not schema:
        raise ValueError(f"No schema for action: {message.action}")
    return schema.model_validate(message.payload)
```

## Serialization

### JSON Serialization

```python
import json
from datetime import datetime

# Pydantic handles serialization automatically
message = AgentMessage(action="task_add", payload={"title": "Test"})

# To JSON string
json_str = message.model_dump_json()

# To dict
data = message.model_dump()

# From JSON
restored = AgentMessage.model_validate_json(json_str)

# From dict
restored = AgentMessage.model_validate(data)
```

### Custom Encoder for Complex Types

```python
from pydantic import ConfigDict

class AgentMessage(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
        },
    )
```

## Message Flow Example

```python
# 1. Client creates message
message = AgentMessage(
    action="task_add",
    payload={"title": "Buy groceries"},
    source_agent="client",
)

# 2. Orchestrator adds correlation ID
message = message.with_correlation(str(uuid4()))

# 3. Target agent processes
response = task_manager.handle_message(message)

# 4. Response includes correlation for tracing
assert response.correlation_id == message.correlation_id
```
