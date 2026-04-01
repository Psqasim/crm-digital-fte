# Pydantic Models for FastAPI

## Request Models

### Basic Create Model

```python
from pydantic import BaseModel, Field
from datetime import datetime

class TaskCreate(BaseModel):
    """Request model for creating a task."""

    title: str = Field(
        ...,  # Required
        min_length=1,
        max_length=200,
        description="The task title",
        examples=["Buy groceries"],
    )
    description: str | None = Field(
        default=None,
        max_length=1000,
        description="Optional task description",
    )
    priority: str = Field(
        default="medium",
        pattern="^(low|medium|high)$",
        description="Task priority level",
    )
```

### Update Model (Partial)

```python
class TaskUpdate(BaseModel):
    """Request model for updating a task (all fields optional)."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    priority: str | None = Field(default=None, pattern="^(low|medium|high)$")
    completed: bool | None = None

    model_config = {"extra": "forbid"}  # Reject unknown fields
```

### Validation

```python
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Self

class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    due_date: datetime | None = None

    @field_validator("title")
    @classmethod
    def title_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Title cannot be empty or whitespace")
        return v.strip()

    @field_validator("due_date")
    @classmethod
    def due_date_must_be_future(cls, v: datetime | None) -> datetime | None:
        if v and v < datetime.utcnow():
            raise ValueError("Due date must be in the future")
        return v

    @model_validator(mode="after")
    def check_consistency(self) -> Self:
        if self.priority == "high" and not self.due_date:
            raise ValueError("High priority tasks must have a due date")
        return self
```

## Response Models

### Basic Response

```python
class TaskResponse(BaseModel):
    """Response model for a task."""

    id: str
    title: str
    description: str | None
    priority: str
    completed: bool
    created_at: datetime
    updated_at: datetime | None

    model_config = {
        "from_attributes": True,  # Enable ORM mode
        "json_schema_extra": {
            "examples": [
                {
                    "id": "task-123",
                    "title": "Buy groceries",
                    "description": "Milk, eggs, bread",
                    "priority": "medium",
                    "completed": False,
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": None,
                }
            ]
        },
    }
```

### Computed Fields

```python
from pydantic import computed_field

class TaskResponse(BaseModel):
    id: str
    title: str
    completed: bool
    created_at: datetime

    model_config = {"from_attributes": True}

    @computed_field
    @property
    def age_days(self) -> int:
        """Days since task was created."""
        delta = datetime.utcnow() - self.created_at
        return delta.days

    @computed_field
    @property
    def status(self) -> str:
        """Human-readable status."""
        return "Done" if self.completed else "Pending"
```

### Nested Models

```python
class UserBrief(BaseModel):
    id: str
    name: str

    model_config = {"from_attributes": True}

class TaskResponse(BaseModel):
    id: str
    title: str
    completed: bool
    assigned_to: UserBrief | None  # Nested model
    tags: list[str]  # List of primitives

    model_config = {"from_attributes": True}
```

## Pagination

### Page Response

```python
from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")

class PageInfo(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_prev: bool

class PageResponse(BaseModel, Generic[T]):
    """Paginated response wrapper."""

    items: list[T]
    page_info: PageInfo

    @classmethod
    def create(
        cls,
        items: list[T],
        page: int,
        page_size: int,
        total_items: int,
    ) -> "PageResponse[T]":
        total_pages = (total_items + page_size - 1) // page_size
        return cls(
            items=items,
            page_info=PageInfo(
                page=page,
                page_size=page_size,
                total_items=total_items,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_prev=page > 1,
            ),
        )

# Usage
@router.get("/tasks", response_model=PageResponse[TaskResponse])
async def list_tasks(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
) -> PageResponse[TaskResponse]:
    total = await count_tasks()
    tasks = await get_tasks(skip=(page - 1) * page_size, limit=page_size)
    return PageResponse.create(tasks, page, page_size, total)
```

## Error Models

### Standard Error Response

```python
class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str = Field(description="Error code")
    message: str = Field(description="Human-readable error message")
    details: dict | None = Field(default=None, description="Additional error details")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "error": "NOT_FOUND",
                    "message": "Task with id 'xyz' not found",
                    "details": None,
                },
                {
                    "error": "VALIDATION_ERROR",
                    "message": "Invalid request data",
                    "details": {"title": ["Field required"]},
                },
            ]
        }
    }
```

### Validation Error Response

```python
class ValidationErrorDetail(BaseModel):
    loc: list[str | int]
    msg: str
    type: str

class ValidationErrorResponse(BaseModel):
    error: str = "VALIDATION_ERROR"
    message: str = "Invalid request data"
    details: list[ValidationErrorDetail]
```

## Enums

### Using Enum

```python
from enum import Enum

class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class TaskCreate(BaseModel):
    title: str
    priority: Priority = Priority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
```

## Serialization

### Custom Serializers

```python
from pydantic import field_serializer

class TaskResponse(BaseModel):
    id: str
    title: str
    created_at: datetime

    @field_serializer("created_at")
    def serialize_datetime(self, value: datetime) -> str:
        return value.strftime("%Y-%m-%d %H:%M:%S")
```

### Alias for JSON Keys

```python
class TaskCreate(BaseModel):
    title: str
    is_completed: bool = Field(default=False, alias="completed")

    model_config = {"populate_by_name": True}

# Accepts both:
# {"title": "Test", "completed": true}
# {"title": "Test", "is_completed": true}
```

## Discriminated Unions

### Polymorphic Models

```python
from typing import Literal, Union
from pydantic import BaseModel, Field

class EmailNotification(BaseModel):
    type: Literal["email"] = "email"
    recipient: str
    subject: str
    body: str

class SlackNotification(BaseModel):
    type: Literal["slack"] = "slack"
    channel: str
    message: str

class WebhookNotification(BaseModel):
    type: Literal["webhook"] = "webhook"
    url: str
    payload: dict

Notification = Union[EmailNotification, SlackNotification, WebhookNotification]

class NotificationCreate(BaseModel):
    notification: Notification = Field(discriminator="type")

# FastAPI automatically handles based on "type" field
@router.post("/notifications")
async def create_notification(data: NotificationCreate) -> dict:
    match data.notification:
        case EmailNotification():
            return await send_email(data.notification)
        case SlackNotification():
            return await send_slack(data.notification)
        case WebhookNotification():
            return await send_webhook(data.notification)
```

## Best Practices

### 1. Separate Request/Response Models

```python
# DON'T share models between request and response
class Task(BaseModel):  # BAD
    id: str | None = None  # Messy optional for create
    title: str
    created_at: datetime | None = None

# DO create separate models
class TaskCreate(BaseModel):  # Request
    title: str

class TaskResponse(BaseModel):  # Response
    id: str
    title: str
    created_at: datetime
```

### 2. Use Field for Documentation

```python
class TaskCreate(BaseModel):
    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="The task title",
        examples=["Buy groceries", "Review PR #123"],
    )
```

### 3. Forbid Extra Fields

```python
class TaskCreate(BaseModel):
    title: str

    model_config = {"extra": "forbid"}

# Rejects: {"title": "Test", "unknown_field": "value"}
```

### 4. Type Coercion Control

```python
class StrictTaskCreate(BaseModel):
    title: str
    count: int

    model_config = {"strict": True}

# Rejects: {"title": "Test", "count": "5"}  # String not coerced to int
```
