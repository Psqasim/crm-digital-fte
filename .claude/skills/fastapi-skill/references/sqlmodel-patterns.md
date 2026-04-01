# SQLModel Patterns

## Overview

SQLModel combines SQLAlchemy and Pydantic, allowing you to define database models that also work as API schemas.

## Setup

### Installation

```bash
pip install sqlmodel aiosqlite  # SQLite async
# or
pip install sqlmodel asyncpg    # PostgreSQL async
```

### Database Configuration

```python
# src/database.py
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite+aiosqlite:///./todo.db"
# PostgreSQL: "postgresql+asyncpg://user:pass@localhost/db"

engine = create_async_engine(DATABASE_URL, echo=True)

async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
```

## Model Definitions

### Basic Model

```python
# src/models/task.py
from sqlmodel import SQLModel, Field
from datetime import datetime
from uuid import uuid4

class Task(SQLModel, table=True):
    """Task database model."""

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    title: str = Field(index=True, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    completed: bool = Field(default=False)
    priority: str = Field(default="medium")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime | None = Field(default=None)
```

### Model with Relationships

```python
from sqlmodel import SQLModel, Field, Relationship

class User(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    email: str = Field(unique=True, index=True)
    name: str

    # Relationship
    tasks: list["Task"] = Relationship(back_populates="owner")

class Task(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    title: str
    completed: bool = Field(default=False)

    # Foreign key
    owner_id: str | None = Field(default=None, foreign_key="user.id")

    # Relationship
    owner: User | None = Relationship(back_populates="tasks")
```

### Many-to-Many Relationship

```python
class TaskTagLink(SQLModel, table=True):
    """Association table for Task-Tag many-to-many."""
    task_id: str = Field(foreign_key="task.id", primary_key=True)
    tag_id: str = Field(foreign_key="tag.id", primary_key=True)

class Tag(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    name: str = Field(unique=True)

    tasks: list["Task"] = Relationship(
        back_populates="tags",
        link_model=TaskTagLink,
    )

class Task(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    title: str

    tags: list[Tag] = Relationship(
        back_populates="tasks",
        link_model=TaskTagLink,
    )
```

## Request/Response Schemas

### Separate Schemas Pattern

```python
# Base model (shared fields)
class TaskBase(SQLModel):
    title: str = Field(max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    priority: str = Field(default="medium")

# Create request (no id, no timestamps)
class TaskCreate(TaskBase):
    pass

# Update request (all optional)
class TaskUpdate(SQLModel):
    title: str | None = None
    description: str | None = None
    priority: str | None = None
    completed: bool | None = None

# Database model
class Task(TaskBase, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    completed: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime | None = None
    owner_id: str | None = Field(default=None, foreign_key="user.id")

# Response (explicit fields for API)
class TaskResponse(TaskBase):
    id: str
    completed: bool
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}
```

## CRUD Operations

### Create

```python
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

async def create_task(db: AsyncSession, task: TaskCreate, owner_id: str) -> Task:
    db_task = Task(
        **task.model_dump(),
        owner_id=owner_id,
    )
    db.add(db_task)
    await db.commit()
    await db.refresh(db_task)
    return db_task
```

### Read

```python
async def get_task(db: AsyncSession, task_id: str) -> Task | None:
    return await db.get(Task, task_id)

async def get_tasks(
    db: AsyncSession,
    owner_id: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Task]:
    query = select(Task)

    if owner_id:
        query = query.where(Task.owner_id == owner_id)

    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()
```

### Update

```python
async def update_task(
    db: AsyncSession,
    task_id: str,
    task_update: TaskUpdate,
) -> Task | None:
    db_task = await db.get(Task, task_id)
    if not db_task:
        return None

    update_data = task_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_task, key, value)

    db_task.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(db_task)
    return db_task
```

### Delete

```python
async def delete_task(db: AsyncSession, task_id: str) -> bool:
    db_task = await db.get(Task, task_id)
    if not db_task:
        return False

    await db.delete(db_task)
    await db.commit()
    return True
```

## Advanced Queries

### Filtering

```python
from sqlmodel import select, or_, and_

async def search_tasks(
    db: AsyncSession,
    search: str | None = None,
    completed: bool | None = None,
    priority: str | None = None,
) -> list[Task]:
    query = select(Task)

    if search:
        query = query.where(
            or_(
                Task.title.ilike(f"%{search}%"),
                Task.description.ilike(f"%{search}%"),
            )
        )

    if completed is not None:
        query = query.where(Task.completed == completed)

    if priority:
        query = query.where(Task.priority == priority)

    result = await db.execute(query)
    return result.scalars().all()
```

### Sorting

```python
from sqlmodel import select, desc, asc

async def get_tasks_sorted(
    db: AsyncSession,
    sort_by: str = "created_at",
    order: str = "desc",
) -> list[Task]:
    query = select(Task)

    sort_column = getattr(Task, sort_by, Task.created_at)
    if order == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(asc(sort_column))

    result = await db.execute(query)
    return result.scalars().all()
```

### Pagination

```python
from sqlmodel import select, func

async def get_tasks_paginated(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 10,
) -> tuple[list[Task], int]:
    # Get total count
    count_query = select(func.count(Task.id))
    total = (await db.execute(count_query)).scalar()

    # Get page
    query = (
        select(Task)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    tasks = result.scalars().all()

    return tasks, total
```

### Eager Loading (Relationships)

```python
from sqlmodel import select
from sqlalchemy.orm import selectinload

async def get_task_with_owner(db: AsyncSession, task_id: str) -> Task | None:
    query = (
        select(Task)
        .where(Task.id == task_id)
        .options(selectinload(Task.owner))
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()

async def get_user_with_tasks(db: AsyncSession, user_id: str) -> User | None:
    query = (
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.tasks))
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()
```

## Service Layer Pattern

```python
# src/services/task_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from src.models.task import Task, TaskCreate, TaskUpdate

class TaskService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: TaskCreate, owner_id: str) -> Task:
        task = Task(**data.model_dump(), owner_id=owner_id)
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def get(self, task_id: str) -> Task | None:
        return await self.db.get(Task, task_id)

    async def list(
        self,
        owner_id: str | None = None,
        completed: bool | None = None,
    ) -> list[Task]:
        query = select(Task)
        if owner_id:
            query = query.where(Task.owner_id == owner_id)
        if completed is not None:
            query = query.where(Task.completed == completed)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def update(self, task_id: str, data: TaskUpdate) -> Task | None:
        task = await self.db.get(Task, task_id)
        if not task:
            return None

        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(task, key, value)

        task.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def delete(self, task_id: str) -> bool:
        task = await self.db.get(Task, task_id)
        if not task:
            return False
        await self.db.delete(task)
        await self.db.commit()
        return True
```

## Transactions

### Explicit Transaction

```python
async def transfer_task(
    db: AsyncSession,
    task_id: str,
    new_owner_id: str,
) -> Task:
    async with db.begin():
        task = await db.get(Task, task_id)
        if not task:
            raise ValueError("Task not found")

        old_owner = await db.get(User, task.owner_id)
        new_owner = await db.get(User, new_owner_id)

        task.owner_id = new_owner_id
        task.updated_at = datetime.utcnow()

        # Both changes committed together or rolled back
        await db.commit()

    await db.refresh(task)
    return task
```

## Migrations with Alembic

### Setup

```bash
pip install alembic
alembic init alembic
```

### Configuration

```python
# alembic/env.py
from sqlmodel import SQLModel
from src.models import *  # Import all models

target_metadata = SQLModel.metadata
```

### Create Migration

```bash
alembic revision --autogenerate -m "Add task table"
alembic upgrade head
```

## Best Practices

### 1. Use Separate Request/Response Models

```python
# DON'T use table model for API
@router.post("/tasks")
async def create_task(task: Task):  # BAD: exposes all fields
    pass

# DO use separate schemas
@router.post("/tasks")
async def create_task(task: TaskCreate) -> TaskResponse:
    pass
```

### 2. Handle Optional Fields Properly

```python
class TaskUpdate(SQLModel):
    title: str | None = None
    # Use exclude_unset to differentiate None from not provided
    # task.model_dump(exclude_unset=True)
```

### 3. Index Frequently Queried Fields

```python
class Task(SQLModel, table=True):
    id: str = Field(primary_key=True)
    title: str = Field(index=True)  # Indexed
    owner_id: str = Field(foreign_key="user.id", index=True)  # Indexed
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
```
