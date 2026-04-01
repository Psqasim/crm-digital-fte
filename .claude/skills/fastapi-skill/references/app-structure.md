# App Structure and Routing

## Application Factory Pattern

### Basic Factory

```python
# src/main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager

from src.routers import tasks, users
from src.database import create_db_and_tables
from src.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    await create_db_and_tables()
    yield
    # Shutdown
    # Clean up resources here

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        description="Task management API",
        lifespan=lifespan,
    )

    # Include routers
    app.include_router(tasks.router, prefix="/api/v1")
    app.include_router(users.router, prefix="/api/v1")

    return app

app = create_app()
```

### Settings with pydantic-settings

```python
# src/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Todo API"
    version: str = "1.0.0"
    debug: bool = False

    # Database
    database_url: str = "sqlite+aiosqlite:///./todo.db"

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # Auth
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

settings = Settings()
```

## Router Organization

### Basic Router

```python
# src/routers/tasks.py
from fastapi import APIRouter, HTTPException, status
from typing import Annotated

from src.schemas.task import TaskCreate, TaskResponse, TaskUpdate
from src.dependencies.database import DB
from src.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.get("", response_model=list[TaskResponse])
async def list_tasks(
    db: DB,
    skip: int = 0,
    limit: int = 100,
    completed: bool | None = None,
) -> list[TaskResponse]:
    """List all tasks with optional filtering."""
    service = TaskService(db)
    return await service.list_tasks(skip=skip, limit=limit, completed=completed)

@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(task: TaskCreate, db: DB) -> TaskResponse:
    """Create a new task."""
    service = TaskService(db)
    return await service.create_task(task)

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, db: DB) -> TaskResponse:
    """Get a task by ID."""
    service = TaskService(db)
    task = await service.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )
    return task

@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(task_id: str, task: TaskUpdate, db: DB) -> TaskResponse:
    """Update a task."""
    service = TaskService(db)
    updated = await service.update_task(task_id, task)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )
    return updated

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: str, db: DB) -> None:
    """Delete a task."""
    service = TaskService(db)
    deleted = await service.delete_task(task_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )
```

### Router with Dependencies

```python
# src/routers/protected.py
from fastapi import APIRouter, Depends
from src.dependencies.auth import get_current_user
from src.models.user import User

router = APIRouter(
    prefix="/protected",
    tags=["protected"],
    dependencies=[Depends(get_current_user)],  # Applies to all routes
)

@router.get("/profile")
async def get_profile(current_user: User = Depends(get_current_user)):
    return {"user": current_user}
```

## Path Operations

### Path Parameters

```python
@router.get("/tasks/{task_id}")
async def get_task(task_id: str) -> TaskResponse:
    pass

# With validation
@router.get("/tasks/{task_id}")
async def get_task(task_id: Annotated[str, Path(min_length=1)]) -> TaskResponse:
    pass

# Multiple parameters
@router.get("/users/{user_id}/tasks/{task_id}")
async def get_user_task(user_id: str, task_id: str) -> TaskResponse:
    pass
```

### Query Parameters

```python
from fastapi import Query
from typing import Annotated

@router.get("/tasks")
async def list_tasks(
    skip: int = 0,
    limit: Annotated[int, Query(le=100)] = 10,
    search: str | None = None,
    completed: bool | None = None,
    sort_by: Annotated[str, Query(regex="^(created_at|title)$")] = "created_at",
) -> list[TaskResponse]:
    pass
```

### Request Body

```python
@router.post("/tasks")
async def create_task(task: TaskCreate) -> TaskResponse:
    # task is validated Pydantic model
    pass

# Multiple body parameters
@router.post("/tasks/{task_id}/assign")
async def assign_task(
    task_id: str,
    assignment: AssignmentCreate,  # Body
) -> TaskResponse:
    pass
```

## Response Handling

### Response Model

```python
@router.get("/tasks", response_model=list[TaskResponse])
async def list_tasks() -> list[TaskResponse]:
    pass

# Exclude fields
@router.get("/users/me", response_model=UserResponse, response_model_exclude={"password_hash"})
async def get_me() -> UserResponse:
    pass

# Include only specific fields
@router.get("/tasks", response_model=list[TaskResponse], response_model_include={"id", "title"})
async def list_tasks_minimal() -> list[TaskResponse]:
    pass
```

### Status Codes

```python
from fastapi import status

@router.post("/tasks", status_code=status.HTTP_201_CREATED)
async def create_task(task: TaskCreate) -> TaskResponse:
    pass

@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: str) -> None:
    pass
```

### Multiple Response Types

```python
from fastapi.responses import JSONResponse

@router.get(
    "/tasks/{task_id}",
    responses={
        200: {"model": TaskResponse},
        404: {"model": ErrorResponse, "description": "Task not found"},
    },
)
async def get_task(task_id: str) -> TaskResponse:
    task = await get_task_by_id(task_id)
    if not task:
        return JSONResponse(
            status_code=404,
            content={"detail": "Task not found"},
        )
    return task
```

## Middleware

### Custom Middleware

```python
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import time

class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()
        response = await call_next(request)
        process_time = time.perf_counter() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response

app.add_middleware(TimingMiddleware)
```

### Request Logging

```python
import structlog

logger = structlog.get_logger()

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
        )

        response = await call_next(request)

        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
        )

        return response
```

## Error Handling

### Exception Handlers

```python
from fastapi import Request
from fastapi.responses import JSONResponse

class NotFoundError(Exception):
    def __init__(self, resource: str, id: str):
        self.resource = resource
        self.id = id

@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError):
    return JSONResponse(
        status_code=404,
        content={
            "error": "NOT_FOUND",
            "message": f"{exc.resource} with id {exc.id} not found",
        },
    )

# Usage
@router.get("/tasks/{task_id}")
async def get_task(task_id: str) -> TaskResponse:
    task = await find_task(task_id)
    if not task:
        raise NotFoundError("Task", task_id)
    return task
```

### Validation Error Handler

```python
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": "VALIDATION_ERROR",
            "message": "Invalid request data",
            "details": exc.errors(),
        },
    )
```

## API Versioning

### URL Prefix Versioning

```python
# src/main.py
from src.routers.v1 import tasks as tasks_v1
from src.routers.v2 import tasks as tasks_v2

app.include_router(tasks_v1.router, prefix="/api/v1")
app.include_router(tasks_v2.router, prefix="/api/v2")
```

### Header Versioning

```python
from fastapi import Header

@router.get("/tasks")
async def list_tasks(
    api_version: str = Header(default="v1", alias="X-API-Version"),
) -> list[TaskResponse]:
    if api_version == "v2":
        return await list_tasks_v2()
    return await list_tasks_v1()
```

## OpenAPI Documentation

### Custom Schema

```python
app = FastAPI(
    title="Todo API",
    description="""
    ## Task Management API

    This API allows you to:
    * Create, read, update, and delete tasks
    * Filter tasks by status
    * Assign tasks to users
    """,
    version="1.0.0",
    contact={
        "name": "API Support",
        "email": "support@example.com",
    },
    license_info={
        "name": "MIT",
    },
)
```

### Route Documentation

```python
@router.post(
    "/tasks",
    response_model=TaskResponse,
    status_code=201,
    summary="Create a new task",
    description="Creates a new task with the provided title and optional description.",
    response_description="The created task",
    tags=["tasks"],
)
async def create_task(task: TaskCreate) -> TaskResponse:
    """
    Create a new task with the following information:

    - **title**: Required. The task title (1-200 characters)
    - **description**: Optional. A detailed description
    - **priority**: Optional. One of: low, medium, high (default: medium)
    """
    pass
```
