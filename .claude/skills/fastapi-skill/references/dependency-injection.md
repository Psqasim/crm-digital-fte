# Dependency Injection with Depends()

## Basic Dependencies

### Simple Dependency

```python
from fastapi import Depends

def get_query_params(skip: int = 0, limit: int = 10) -> dict:
    return {"skip": skip, "limit": limit}

@router.get("/tasks")
async def list_tasks(params: dict = Depends(get_query_params)):
    return await get_tasks(skip=params["skip"], limit=params["limit"])
```

### Class-Based Dependency

```python
class QueryParams:
    def __init__(self, skip: int = 0, limit: int = 10, search: str | None = None):
        self.skip = skip
        self.limit = limit
        self.search = search

@router.get("/tasks")
async def list_tasks(params: QueryParams = Depends()):
    return await get_tasks(
        skip=params.skip,
        limit=params.limit,
        search=params.search,
    )
```

## Database Session

### Async Session Dependency

```python
# src/dependencies/database.py
from typing import Annotated, AsyncGenerator
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import async_session_maker

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

# Type alias for cleaner signatures
DB = Annotated[AsyncSession, Depends(get_db)]
```

### Usage

```python
from src.dependencies.database import DB

@router.get("/tasks")
async def list_tasks(db: DB) -> list[TaskResponse]:
    result = await db.execute(select(Task))
    return result.scalars().all()

@router.post("/tasks")
async def create_task(task: TaskCreate, db: DB) -> TaskResponse:
    new_task = Task(**task.model_dump())
    db.add(new_task)
    await db.flush()  # Get ID before commit
    await db.refresh(new_task)
    return new_task
```

## Authentication

### Get Current User

```python
# src/dependencies/auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Annotated

from src.services.auth import verify_token
from src.models.user import User

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: DB = Depends(get_db),
) -> User:
    """Extract and verify the current user from JWT token."""
    token = credentials.credentials

    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await db.get(User, payload["sub"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user

# Type alias
CurrentUser = Annotated[User, Depends(get_current_user)]
```

### Usage

```python
from src.dependencies.auth import CurrentUser

@router.get("/me")
async def get_profile(user: CurrentUser) -> UserResponse:
    return user

@router.get("/my-tasks")
async def get_my_tasks(user: CurrentUser, db: DB) -> list[TaskResponse]:
    result = await db.execute(
        select(Task).where(Task.user_id == user.id)
    )
    return result.scalars().all()
```

### Optional Authentication

```python
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer(auto_error=False)

async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: DB = Depends(get_db),
) -> User | None:
    """Get user if authenticated, None otherwise."""
    if not credentials:
        return None

    payload = verify_token(credentials.credentials)
    if not payload:
        return None

    return await db.get(User, payload["sub"])

OptionalUser = Annotated[User | None, Depends(get_optional_user)]

@router.get("/tasks")
async def list_tasks(user: OptionalUser, db: DB) -> list[TaskResponse]:
    query = select(Task)
    if user:
        # Show all tasks including private ones for authenticated users
        pass
    else:
        # Only show public tasks
        query = query.where(Task.is_public == True)
    result = await db.execute(query)
    return result.scalars().all()
```

## Service Dependencies

### Service with Dependencies

```python
# src/services/task_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.task import Task
from src.schemas.task import TaskCreate, TaskUpdate

class TaskService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_task(self, data: TaskCreate, user_id: str) -> Task:
        task = Task(**data.model_dump(), user_id=user_id)
        self.db.add(task)
        await self.db.flush()
        await self.db.refresh(task)
        return task

    async def get_task(self, task_id: str) -> Task | None:
        return await self.db.get(Task, task_id)

    async def list_tasks(
        self,
        user_id: str | None = None,
        completed: bool | None = None,
    ) -> list[Task]:
        query = select(Task)
        if user_id:
            query = query.where(Task.user_id == user_id)
        if completed is not None:
            query = query.where(Task.completed == completed)
        result = await self.db.execute(query)
        return result.scalars().all()
```

### Service Dependency Factory

```python
# src/dependencies/services.py
from typing import Annotated
from fastapi import Depends

from src.dependencies.database import DB
from src.services.task_service import TaskService

def get_task_service(db: DB) -> TaskService:
    return TaskService(db)

TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]
```

### Usage

```python
from src.dependencies.services import TaskServiceDep
from src.dependencies.auth import CurrentUser

@router.get("/tasks")
async def list_tasks(
    service: TaskServiceDep,
    user: CurrentUser,
    completed: bool | None = None,
) -> list[TaskResponse]:
    return await service.list_tasks(user_id=user.id, completed=completed)

@router.post("/tasks")
async def create_task(
    task: TaskCreate,
    service: TaskServiceDep,
    user: CurrentUser,
) -> TaskResponse:
    return await service.create_task(task, user_id=user.id)
```

## Scoped Dependencies

### Request-Scoped (Default)

```python
# Each request gets a new instance
@router.get("/tasks")
async def list_tasks(db: DB):  # New session per request
    pass
```

### Application-Scoped (Singleton)

```python
# Shared across all requests
from functools import lru_cache

class Settings:
    def __init__(self):
        self.app_name = "Todo API"

@lru_cache
def get_settings() -> Settings:
    return Settings()

@router.get("/info")
async def get_info(settings: Settings = Depends(get_settings)):
    return {"app_name": settings.app_name}
```

## Dependency Overrides (Testing)

### Override for Tests

```python
# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from src.main import app
from src.dependencies.database import get_db

# Test database
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

@pytest.fixture
def client():
    async def override_get_db():
        engine = create_async_engine(TEST_DATABASE_URL)
        async with AsyncSession(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
```

### Mock Authentication

```python
from src.dependencies.auth import get_current_user
from src.models.user import User

@pytest.fixture
def authenticated_client(client):
    fake_user = User(id="test-user", email="test@example.com")

    async def override_get_current_user():
        return fake_user

    app.dependency_overrides[get_current_user] = override_get_current_user

    yield client

    app.dependency_overrides.clear()
```

## Sub-Dependencies

### Chained Dependencies

```python
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session

async def get_current_user(db: DB) -> User:
    # Uses get_db dependency
    pass

async def get_user_permissions(user: CurrentUser, db: DB) -> list[str]:
    # Uses get_current_user which uses get_db
    result = await db.execute(
        select(Permission.name).where(Permission.user_id == user.id)
    )
    return result.scalars().all()

@router.get("/admin")
async def admin_panel(
    permissions: list[str] = Depends(get_user_permissions),
):
    if "admin" not in permissions:
        raise HTTPException(status_code=403, detail="Admin access required")
    return {"message": "Welcome, admin"}
```

## Path Operation Dependencies

### Route-Level Dependencies

```python
async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != "secret-key":
        raise HTTPException(status_code=403, detail="Invalid API key")

@router.get("/external", dependencies=[Depends(verify_api_key)])
async def external_endpoint():
    return {"message": "Authenticated via API key"}
```

### Router-Level Dependencies

```python
# All routes in this router require authentication
router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(get_current_user)],
)

@router.get("/users")
async def list_users(db: DB):  # Already authenticated
    pass
```

### App-Level Dependencies

```python
app = FastAPI(dependencies=[Depends(log_requests)])
# All routes will have logging
```

## Best Practices

### 1. Use Annotated for Clean Signatures

```python
from typing import Annotated

# Define once
DB = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]

# Use everywhere
@router.get("/tasks")
async def list_tasks(db: DB, user: CurrentUser):
    pass
```

### 2. Keep Dependencies Focused

```python
# GOOD: Single responsibility
async def get_db(): ...
async def get_current_user(db): ...
async def get_task_service(db): ...

# BAD: Too many responsibilities
async def get_everything(db, user, config, logger): ...
```

### 3. Handle Cleanup Properly

```python
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()  # Success
        except Exception:
            await session.rollback()  # Failure
            raise
        # Session closed automatically by context manager
```
