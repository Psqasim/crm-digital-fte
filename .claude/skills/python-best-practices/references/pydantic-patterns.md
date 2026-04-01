# Pydantic Patterns

## Table of Contents
- [Model Basics](#model-basics)
- [Validators](#validators)
- [Field Constraints](#field-constraints)
- [Serialization](#serialization)
- [Settings Management](#settings-management)

## Model Basics

### Simple Model

```python
from datetime import datetime
from pydantic import BaseModel, Field

class Task(BaseModel):
    """Task entity with automatic validation."""

    id: int
    title: str
    description: str | None = None
    completed: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

# Create from dict
task = Task(**{"id": 1, "title": "Buy groceries"})

# Create with kwargs
task = Task(id=1, title="Buy groceries")

# Validation happens automatically
task = Task(id="not-an-int", title="Test")  # Raises ValidationError
```

### Model Config

```python
class Task(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,  # Strip whitespace from strings
        frozen=True,                # Immutable instances
        extra="forbid",             # Error on unknown fields
        validate_default=True,      # Validate default values
    )

    id: int
    title: str
```

### Nested Models

```python
class Address(BaseModel):
    street: str
    city: str
    country: str = "USA"

class User(BaseModel):
    name: str
    email: str
    address: Address  # Nested model

# Automatic nested validation
user = User(
    name="John",
    email="john@example.com",
    address={"street": "123 Main", "city": "Boston"}
)
```

## Validators

### Field Validators (Pydantic v2)

```python
from pydantic import BaseModel, field_validator

class Task(BaseModel):
    title: str
    priority: int

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Title cannot be empty")
        return v.strip()

    @field_validator("priority")
    @classmethod
    def priority_range(cls, v: int) -> int:
        if not 1 <= v <= 5:
            raise ValueError("Priority must be 1-5")
        return v
```

### Model Validators

```python
from pydantic import BaseModel, model_validator

class DateRange(BaseModel):
    start: datetime
    end: datetime

    @model_validator(mode="after")
    def end_after_start(self) -> "DateRange":
        if self.end <= self.start:
            raise ValueError("End must be after start")
        return self
```

### Before vs After Validators

```python
class User(BaseModel):
    email: str

    # Before: runs before Pydantic's validation
    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.lower().strip()

    # After: runs after Pydantic validates type
    @field_validator("email", mode="after")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        if not v.endswith("@company.com"):
            raise ValueError("Must use company email")
        return v
```

## Field Constraints

### Using Field()

```python
from pydantic import BaseModel, Field

class Task(BaseModel):
    # String constraints
    title: str = Field(min_length=1, max_length=200)

    # Numeric constraints
    priority: int = Field(ge=1, le=5, default=3)

    # Pattern matching
    code: str = Field(pattern=r"^[A-Z]{3}-\d{4}$")

    # Default factory
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Documentation
    status: str = Field(
        default="pending",
        description="Current task status",
        examples=["pending", "in_progress", "done"]
    )
```

### Annotated Types (Python 3.9+)

```python
from typing import Annotated
from pydantic import Field

# Reusable type aliases
TaskTitle = Annotated[str, Field(min_length=1, max_length=200)]
Priority = Annotated[int, Field(ge=1, le=5)]

class Task(BaseModel):
    title: TaskTitle
    priority: Priority = 3
```

## Serialization

### To Dict/JSON

```python
task = Task(id=1, title="Test")

# To dict
data = task.model_dump()
# {"id": 1, "title": "Test", "completed": False, ...}

# Exclude fields
data = task.model_dump(exclude={"created_at"})

# Include only specific fields
data = task.model_dump(include={"id", "title"})

# To JSON string
json_str = task.model_dump_json()

# Pretty JSON
json_str = task.model_dump_json(indent=2)
```

### From Dict/JSON

```python
# From dict
task = Task.model_validate({"id": 1, "title": "Test"})

# From JSON string
task = Task.model_validate_json('{"id": 1, "title": "Test"}')

# Strict mode (no type coercion)
task = Task.model_validate(data, strict=True)
```

### Alias for API Compatibility

```python
class APIResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    task_id: int = Field(alias="taskId")  # Accept "taskId" from API
    created_at: datetime = Field(alias="createdAt")

# Accepts both field name and alias
response = APIResponse(taskId=1, createdAt="2025-01-01T00:00:00")

# Serialize with aliases
data = response.model_dump(by_alias=True)
# {"taskId": 1, "createdAt": "2025-01-01T00:00:00"}
```

## Settings Management

### Environment-based Config

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    database_url: str
    api_key: str
    debug: bool = False
    max_connections: int = 10

# Reads from environment variables
# DATABASE_URL, API_KEY, DEBUG, MAX_CONNECTIONS
settings = Settings()
```

### Nested Settings

```python
class DatabaseSettings(BaseSettings):
    host: str = "localhost"
    port: int = 5432
    name: str

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_nested_delimiter="__")

    database: DatabaseSettings

# Set via: DATABASE__HOST, DATABASE__PORT, DATABASE__NAME
settings = Settings()
```

### Computed Fields

```python
from pydantic import BaseModel, computed_field

class Rectangle(BaseModel):
    width: float
    height: float

    @computed_field
    @property
    def area(self) -> float:
        return self.width * self.height

rect = Rectangle(width=10, height=5)
print(rect.area)  # 50.0
print(rect.model_dump())  # {"width": 10, "height": 5, "area": 50.0}
```
