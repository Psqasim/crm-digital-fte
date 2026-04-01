# Async Testing with pytest-asyncio

## Setup

### Installation

```bash
uv add --dev pytest-asyncio
```

### Configuration

```toml
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"  # Automatically handle async tests
asyncio_default_fixture_loop_scope = "function"
```

## Basic Async Tests

### Auto Mode (Recommended)

```python
import pytest

# With asyncio_mode = "auto", no decorator needed
async def test_async_operation() -> None:
    result = await async_fetch_data()
    assert result is not None

async def test_async_with_await() -> None:
    task = await create_task_async("Test")
    assert task.title == "Test"
```

### Explicit Mode

```python
import pytest

@pytest.mark.asyncio
async def test_explicit_async() -> None:
    """Use when asyncio_mode is not 'auto'."""
    result = await async_operation()
    assert result == "expected"
```

## Async Fixtures

### Basic Async Fixture

```python
import pytest

@pytest.fixture
async def async_storage() -> AsyncStorage:
    """Async fixture for storage."""
    storage = AsyncStorage()
    await storage.connect()
    return storage

@pytest.fixture
async def async_task_manager(async_storage: AsyncStorage) -> AsyncTaskManager:
    """Fixtures can depend on other async fixtures."""
    return AsyncTaskManager(storage=async_storage)

async def test_async_create(async_task_manager: AsyncTaskManager) -> None:
    task = await async_task_manager.create_task("Test")
    assert task.id is not None
```

### Async Fixture with Cleanup

```python
from collections.abc import AsyncGenerator

@pytest.fixture
async def database() -> AsyncGenerator[Database, None]:
    """Use async generator for cleanup."""
    db = Database()
    await db.connect()
    yield db
    await db.disconnect()

@pytest.fixture
async def transaction(database: Database) -> AsyncGenerator[Transaction, None]:
    """Nested async fixture with rollback."""
    tx = await database.begin_transaction()
    yield tx
    await tx.rollback()
```

### Session-Scoped Async Fixtures

```python
@pytest.fixture(scope="session")
async def shared_connection() -> AsyncGenerator[Connection, None]:
    """Expensive connection shared across all tests."""
    conn = await create_connection()
    yield conn
    await conn.close()
```

## Testing Async Patterns

### Testing Concurrent Operations

```python
import asyncio

async def test_concurrent_tasks() -> None:
    """Test multiple async operations."""
    async with AsyncTaskManager() as manager:
        # Create tasks concurrently
        results = await asyncio.gather(
            manager.create_task("Task 1"),
            manager.create_task("Task 2"),
            manager.create_task("Task 3"),
        )

        assert len(results) == 3
        assert all(task.id is not None for task in results)
```

### Testing with Timeouts

```python
import asyncio
import pytest

async def test_with_timeout() -> None:
    """Ensure operation completes within timeout."""
    async with asyncio.timeout(1.0):
        result = await fast_operation()
        assert result is not None

async def test_timeout_raises() -> None:
    """Test that slow operations timeout."""
    with pytest.raises(asyncio.TimeoutError):
        async with asyncio.timeout(0.1):
            await slow_operation()
```

### Testing TaskGroups

```python
import asyncio

async def test_task_group_success() -> None:
    """Test TaskGroup for concurrent work."""
    results: list[Task] = []

    async with asyncio.TaskGroup() as tg:
        for i in range(3):
            tg.create_task(create_and_append(f"Task {i}", results))

    assert len(results) == 3

async def test_task_group_exception() -> None:
    """TaskGroup cancels all on first exception."""
    with pytest.raises(ExceptionGroup) as exc_info:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(successful_task())
            tg.create_task(failing_task())

    assert len(exc_info.value.exceptions) >= 1
```

## Mocking Async Code

### AsyncMock

```python
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_async_storage() -> AsyncMock:
    """Create async mock for storage."""
    storage = AsyncMock()
    storage.get.return_value = Task(id="1", title="Test")
    storage.save.return_value = None
    return storage

async def test_with_async_mock(mock_async_storage: AsyncMock) -> None:
    manager = AsyncTaskManager(storage=mock_async_storage)

    task = await manager.get_task("1")

    mock_async_storage.get.assert_awaited_once_with("1")
    assert task.title == "Test"
```

### Async Side Effects

```python
async def test_async_side_effect() -> None:
    mock = AsyncMock()

    # Return different values on successive calls
    mock.fetch.side_effect = [
        {"status": "pending"},
        {"status": "complete"},
    ]

    result1 = await mock.fetch()
    result2 = await mock.fetch()

    assert result1["status"] == "pending"
    assert result2["status"] == "complete"

async def test_async_exception() -> None:
    mock = AsyncMock()
    mock.fetch.side_effect = ConnectionError("Network failure")

    with pytest.raises(ConnectionError):
        await mock.fetch()
```

### Patching Async Functions

```python
from unittest.mock import patch, AsyncMock

async def test_patch_async_function() -> None:
    with patch(
        "src.services.api_client.fetch_data",
        new_callable=AsyncMock,
        return_value={"data": "test"},
    ) as mock_fetch:
        result = await fetch_and_process()

        mock_fetch.assert_awaited_once()
        assert result == "processed: test"
```

## Testing Async Context Managers

```python
async def test_async_context_manager() -> None:
    """Test async with statement."""
    async with AsyncResourceManager() as resource:
        assert resource.is_connected
        await resource.do_work()

    assert not resource.is_connected  # Verify cleanup

async def test_context_manager_exception() -> None:
    """Test cleanup happens on exception."""
    resource = None
    with pytest.raises(ValueError):
        async with AsyncResourceManager() as resource:
            raise ValueError("Test error")

    assert not resource.is_connected  # Cleanup still happened
```

## Testing Event Loops

### Custom Event Loop Policy

```python
import pytest
import asyncio

@pytest.fixture(scope="session")
def event_loop_policy():
    """Use uvloop for faster tests if available."""
    try:
        import uvloop
        return uvloop.EventLoopPolicy()
    except ImportError:
        return asyncio.DefaultEventLoopPolicy()
```

### Testing with Multiple Loops

```python
async def test_independent_operations() -> None:
    """Each test gets fresh event loop."""
    # This test's loop is isolated from other tests
    result = await async_operation()
    assert result is not None
```

## Common Pitfalls

### Forgetting to Await

```python
# WRONG - assertion passes because it's checking coroutine object
async def test_wrong() -> None:
    result = async_fetch()  # Missing await!
    assert result  # Always truthy (coroutine object)

# CORRECT
async def test_correct() -> None:
    result = await async_fetch()
    assert result
```

### Mixing Sync and Async

```python
# If you need to call async from sync fixture
@pytest.fixture
def sync_fixture(event_loop: asyncio.AbstractEventLoop) -> Data:
    return event_loop.run_until_complete(async_setup())

# Better: use async fixture
@pytest.fixture
async def async_fixture() -> Data:
    return await async_setup()
```
