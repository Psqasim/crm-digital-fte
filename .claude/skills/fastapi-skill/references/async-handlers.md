# Async Route Handlers

## Async vs Sync Handlers

### When to Use Async

```python
# USE ASYNC when:
# - Making HTTP requests
# - Database operations with async driver
# - File I/O with aiofiles
# - Any awaitable operations

@router.get("/tasks")
async def list_tasks(db: DB) -> list[TaskResponse]:
    result = await db.execute(select(Task))  # Async DB
    return result.scalars().all()

@router.get("/external")
async def fetch_external() -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.example.com/data")
        return response.json()
```

### When to Use Sync

```python
# USE SYNC when:
# - CPU-bound operations only
# - No I/O operations
# - Using sync-only libraries

@router.get("/compute")
def compute_hash(data: str) -> dict:
    # CPU-bound, no I/O
    result = hashlib.sha256(data.encode()).hexdigest()
    return {"hash": result}
```

## Database Operations

### Async SQLAlchemy

```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Setup
engine = create_async_engine(
    "postgresql+asyncpg://user:pass@localhost/db",
    echo=True,
)

async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Usage
@router.get("/tasks/{task_id}")
async def get_task(task_id: str, db: DB) -> TaskResponse:
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404)
    return task

@router.post("/tasks")
async def create_task(task: TaskCreate, db: DB) -> TaskResponse:
    new_task = Task(**task.model_dump())
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)
    return new_task
```

### Async Queries

```python
from sqlalchemy import select, func

@router.get("/tasks")
async def list_tasks(
    db: DB,
    skip: int = 0,
    limit: int = 10,
    completed: bool | None = None,
) -> list[TaskResponse]:
    query = select(Task)

    if completed is not None:
        query = query.where(Task.completed == completed)

    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()

@router.get("/tasks/count")
async def count_tasks(db: DB) -> dict:
    result = await db.execute(select(func.count(Task.id)))
    return {"count": result.scalar()}
```

## HTTP Client Operations

### Using httpx

```python
import httpx
from typing import Any

# Shared client (for connection pooling)
http_client = httpx.AsyncClient(timeout=30.0)

@router.on_event("shutdown")
async def shutdown_event():
    await http_client.aclose()

@router.get("/weather/{city}")
async def get_weather(city: str) -> dict:
    response = await http_client.get(
        f"https://api.weather.com/v1/{city}",
        headers={"Authorization": f"Bearer {settings.weather_api_key}"},
    )
    response.raise_for_status()
    return response.json()
```

### Parallel Requests

```python
import asyncio

@router.get("/dashboard")
async def get_dashboard(user_id: str) -> dict:
    # Fetch multiple resources in parallel
    tasks_coro = fetch_tasks(user_id)
    notifications_coro = fetch_notifications(user_id)
    stats_coro = fetch_stats(user_id)

    tasks, notifications, stats = await asyncio.gather(
        tasks_coro,
        notifications_coro,
        stats_coro,
    )

    return {
        "tasks": tasks,
        "notifications": notifications,
        "stats": stats,
    }
```

### With Error Handling

```python
import asyncio

@router.get("/dashboard")
async def get_dashboard(user_id: str) -> dict:
    results = await asyncio.gather(
        fetch_tasks(user_id),
        fetch_notifications(user_id),
        fetch_stats(user_id),
        return_exceptions=True,  # Don't fail if one fails
    )

    tasks, notifications, stats = results

    return {
        "tasks": tasks if not isinstance(tasks, Exception) else [],
        "notifications": notifications if not isinstance(notifications, Exception) else [],
        "stats": stats if not isinstance(stats, Exception) else {},
    }
```

## File Operations

### Async File Reading

```python
import aiofiles

@router.get("/logs/{filename}")
async def read_log(filename: str) -> dict:
    filepath = f"/var/logs/{filename}"

    try:
        async with aiofiles.open(filepath, "r") as f:
            content = await f.read()
        return {"content": content}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Log file not found")
```

### Async File Upload

```python
from fastapi import UploadFile
import aiofiles

@router.post("/upload")
async def upload_file(file: UploadFile) -> dict:
    filepath = f"/uploads/{file.filename}"

    async with aiofiles.open(filepath, "wb") as out_file:
        content = await file.read()
        await out_file.write(content)

    return {"filename": file.filename, "size": len(content)}
```

### Streaming Large Files

```python
from fastapi.responses import StreamingResponse
import aiofiles

@router.get("/download/{filename}")
async def download_file(filename: str) -> StreamingResponse:
    filepath = f"/files/{filename}"

    async def file_stream():
        async with aiofiles.open(filepath, "rb") as f:
            while chunk := await f.read(8192):  # 8KB chunks
                yield chunk

    return StreamingResponse(
        file_stream(),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
```

## Background Tasks

### Simple Background Task

```python
from fastapi import BackgroundTasks

async def send_notification(user_id: str, message: str):
    """Background task to send notification."""
    await asyncio.sleep(1)  # Simulate delay
    print(f"Sent to {user_id}: {message}")

@router.post("/tasks")
async def create_task(
    task: TaskCreate,
    background_tasks: BackgroundTasks,
    db: DB,
) -> TaskResponse:
    new_task = await save_task(db, task)

    # Queue notification (runs after response is sent)
    background_tasks.add_task(
        send_notification,
        user_id=task.user_id,
        message=f"Task '{task.title}' created",
    )

    return new_task
```

### Multiple Background Tasks

```python
@router.post("/tasks/{task_id}/complete")
async def complete_task(
    task_id: str,
    background_tasks: BackgroundTasks,
    db: DB,
) -> TaskResponse:
    task = await mark_completed(db, task_id)

    # Queue multiple tasks
    background_tasks.add_task(send_email, task.user_email, "Task completed!")
    background_tasks.add_task(update_stats, task.user_id)
    background_tasks.add_task(log_activity, "task_completed", task_id)

    return task
```

## Timeouts

### Request Timeout

```python
import asyncio

@router.get("/slow-external")
async def fetch_slow_external() -> dict:
    try:
        async with asyncio.timeout(5.0):  # 5 second timeout
            result = await slow_external_api()
            return result
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="External service timeout",
        )
```

### Per-Operation Timeout

```python
@router.get("/aggregate")
async def aggregate_data() -> dict:
    async def fetch_with_timeout(coro, timeout: float, default):
        try:
            async with asyncio.timeout(timeout):
                return await coro
        except asyncio.TimeoutError:
            return default

    # Different timeouts for different operations
    tasks = await fetch_with_timeout(fetch_tasks(), 2.0, [])
    users = await fetch_with_timeout(fetch_users(), 3.0, [])
    stats = await fetch_with_timeout(fetch_stats(), 1.0, {})

    return {"tasks": tasks, "users": users, "stats": stats}
```

## Concurrency Control

### Semaphore for Rate Limiting

```python
import asyncio

# Limit concurrent requests to external API
semaphore = asyncio.Semaphore(10)

async def fetch_with_limit(url: str) -> dict:
    async with semaphore:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            return response.json()

@router.get("/batch")
async def batch_fetch(urls: list[str]) -> list[dict]:
    tasks = [fetch_with_limit(url) for url in urls]
    return await asyncio.gather(*tasks)
```

### Connection Pool

```python
from contextlib import asynccontextmanager

# Reuse connections
@asynccontextmanager
async def get_http_client():
    async with httpx.AsyncClient(
        limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
        timeout=httpx.Timeout(30.0),
    ) as client:
        yield client

@router.get("/external/{resource}")
async def fetch_resource(resource: str) -> dict:
    async with get_http_client() as client:
        response = await client.get(f"https://api.example.com/{resource}")
        return response.json()
```

## Error Handling

### Async Exception Handling

```python
@router.get("/tasks/{task_id}")
async def get_task(task_id: str, db: DB) -> TaskResponse:
    try:
        task = await db.get(Task, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return task
    except SQLAlchemyError as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Database error")
```

### Cleanup with try/finally

```python
@router.post("/process")
async def process_data(data: ProcessInput) -> dict:
    temp_file = None
    try:
        temp_file = await create_temp_file(data)
        result = await process_file(temp_file)
        return {"result": result}
    except ProcessingError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        if temp_file:
            await cleanup_temp_file(temp_file)
```

## Best Practices

### 1. Always Await Coroutines

```python
# BAD: Forgetting await
@router.get("/tasks")
async def list_tasks(db: DB):
    return db.execute(select(Task))  # Returns coroutine, not result!

# GOOD: Proper await
@router.get("/tasks")
async def list_tasks(db: DB):
    result = await db.execute(select(Task))
    return result.scalars().all()
```

### 2. Don't Block the Event Loop

```python
# BAD: Blocking call in async handler
@router.get("/hash")
async def compute_hash(data: str):
    time.sleep(5)  # Blocks event loop!
    return {"hash": hashlib.sha256(data.encode()).hexdigest()}

# GOOD: Use sync handler for CPU-bound work
@router.get("/hash")
def compute_hash(data: str):  # sync, runs in thread pool
    time.sleep(5)  # OK in sync handler
    return {"hash": hashlib.sha256(data.encode()).hexdigest()}

# GOOD: Or run in executor
@router.get("/hash")
async def compute_hash(data: str):
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, compute_expensive, data)
    return {"hash": result}
```

### 3. Use Context Managers

```python
# GOOD: Proper resource cleanup
@router.get("/data")
async def get_data():
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.json()
    # Client is automatically closed
```
