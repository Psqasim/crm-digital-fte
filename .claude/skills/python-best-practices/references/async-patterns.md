# Async Patterns

## Table of Contents
- [Fundamentals](#fundamentals)
- [Concurrent Execution](#concurrent-execution)
- [Context Managers](#context-managers)
- [Common Pitfalls](#common-pitfalls)

## Fundamentals

### Basic async/await

```python
import asyncio

async def fetch_data(url: str) -> dict:
    """Async functions return coroutines."""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()

# Call with await
data = await fetch_data("https://api.example.com")

# Or run from sync code
data = asyncio.run(fetch_data("https://api.example.com"))
```

### Async Generators

```python
async def stream_items() -> AsyncIterator[Item]:
    """Yield items asynchronously."""
    async for record in database.stream():
        yield Item.from_record(record)

# Consume
async for item in stream_items():
    process(item)
```

## Concurrent Execution

### asyncio.gather (Python 3.11+)

Run multiple coroutines concurrently:

```python
async def fetch_all(urls: list[str]) -> list[dict]:
    """Fetch multiple URLs concurrently."""
    results = await asyncio.gather(
        *[fetch_data(url) for url in urls],
        return_exceptions=True  # Don't fail on single error
    )
    return [r for r in results if not isinstance(r, Exception)]
```

### TaskGroup (Python 3.11+, preferred)

Structured concurrency with automatic cancellation:

```python
async def process_batch(items: list[Item]) -> list[Result]:
    """Process items with proper cleanup on failure."""
    results: list[Result] = []

    async with asyncio.TaskGroup() as tg:
        for item in items:
            tg.create_task(process_item(item, results))

    return results
```

TaskGroup benefits:
- Automatic cancellation if any task fails
- All exceptions collected and raised as ExceptionGroup
- Cleaner than manual gather + exception handling

### Semaphore for Rate Limiting

```python
async def fetch_with_limit(urls: list[str], max_concurrent: int = 10) -> list[dict]:
    """Limit concurrent requests."""
    semaphore = asyncio.Semaphore(max_concurrent)

    async def limited_fetch(url: str) -> dict:
        async with semaphore:
            return await fetch_data(url)

    return await asyncio.gather(*[limited_fetch(url) for url in urls])
```

## Context Managers

### Async Context Manager

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def database_transaction():
    """Async context manager for transactions."""
    conn = await get_connection()
    try:
        yield conn
        await conn.commit()
    except Exception:
        await conn.rollback()
        raise
    finally:
        await conn.close()

# Usage
async with database_transaction() as conn:
    await conn.execute("INSERT ...")
```

### Class-based Async Context Manager

```python
class AsyncResource:
    async def __aenter__(self) -> "AsyncResource":
        await self._setup()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        await self._cleanup()
        return False  # Don't suppress exceptions
```

## Common Pitfalls

### 1. Blocking the Event Loop

```python
# BAD: Blocks event loop
def sync_db_call():
    time.sleep(1)  # Blocks!
    return database.query()

# GOOD: Use async or run in executor
async def async_db_call():
    return await asyncio.to_thread(sync_db_call)
```

### 2. Forgotten await

```python
# BAD: Returns coroutine, not result
result = fetch_data(url)  # Missing await!

# GOOD
result = await fetch_data(url)
```

### 3. Creating Tasks Without Awaiting

```python
# BAD: Task may be garbage collected
asyncio.create_task(background_job())

# GOOD: Store reference or use TaskGroup
task = asyncio.create_task(background_job())
# ... later
await task
```

### 4. Mixing Sync and Async

```python
# BAD: Calling async from sync without asyncio.run
def sync_function():
    data = fetch_data(url)  # Returns coroutine!

# GOOD: Bridge properly
def sync_function():
    return asyncio.run(fetch_data(url))

# OR make the caller async
async def async_function():
    return await fetch_data(url)
```

### 5. Not Handling Cancellation

```python
async def cancellable_task():
    """Handle cancellation gracefully."""
    try:
        while True:
            await process_item()
    except asyncio.CancelledError:
        await cleanup()  # Cleanup before re-raising
        raise
```
