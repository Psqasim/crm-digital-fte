# Mocking Patterns

## Test Doubles Overview

| Double | Purpose | When to Use |
|--------|---------|-------------|
| **Stub** | Returns predetermined values | Control indirect inputs |
| **Mock** | Verifies interactions | Verify method calls |
| **Fake** | Working implementation | In-memory database |
| **Spy** | Records calls to real object | Observe without replacing |

## unittest.mock Basics

### MagicMock

```python
from unittest.mock import MagicMock, Mock

def test_with_mock() -> None:
    # Create mock with return value
    storage = MagicMock()
    storage.get.return_value = Task(id="1", title="Test")

    # Use in code under test
    manager = TaskManager(storage=storage)
    task = manager.get_task("1")

    # Verify interactions
    storage.get.assert_called_once_with("1")
    assert task.title == "Test"
```

### Configuring Return Values

```python
mock = MagicMock()

# Simple return value
mock.method.return_value = "result"

# Different values per call
mock.method.side_effect = ["first", "second", "third"]

# Raise exception
mock.method.side_effect = ValueError("Invalid input")

# Conditional return based on input
def conditional_return(key: str) -> str:
    return {"a": "1", "b": "2"}.get(key, "default")

mock.method.side_effect = conditional_return
```

### Assertions

```python
mock = MagicMock()
mock.method("arg1", key="value")

# Verify calls
mock.method.assert_called()
mock.method.assert_called_once()
mock.method.assert_called_with("arg1", key="value")
mock.method.assert_called_once_with("arg1", key="value")

# Call count and history
assert mock.method.call_count == 1
assert mock.method.call_args == call("arg1", key="value")
assert mock.method.call_args_list == [call("arg1", key="value")]

# Not called
mock.other_method.assert_not_called()
```

## Patching

### patch Decorator

```python
from unittest.mock import patch

@patch("src.services.task_manager.StorageAgent")
def test_with_patched_storage(MockStorage: MagicMock) -> None:
    mock_instance = MockStorage.return_value
    mock_instance.get.return_value = Task(id="1", title="Test")

    manager = TaskManager()
    task = manager.get_task("1")

    assert task.title == "Test"
```

### patch Context Manager

```python
def test_with_context_manager() -> None:
    with patch("src.services.external_api.requests.get") as mock_get:
        mock_get.return_value.json.return_value = {"status": "ok"}

        result = fetch_status()

        assert result == "ok"
```

### patch.object

```python
def test_patch_specific_method() -> None:
    storage = InMemoryStorage()

    with patch.object(storage, "get", return_value=Task(id="1", title="Test")):
        task = storage.get("1")
        assert task.title == "Test"
```

### Patch Where Used, Not Defined

```python
# WRONG: Patching where defined
@patch("src.utils.helpers.datetime")  # Won't work!
def test_wrong() -> None:
    pass

# CORRECT: Patch where imported/used
@patch("src.services.task_manager.datetime")  # Works!
def test_correct() -> None:
    pass
```

## pytest-mock (Recommended)

```python
from pytest_mock import MockerFixture

def test_with_mocker(mocker: MockerFixture) -> None:
    # Cleaner syntax, automatic cleanup
    mock_storage = mocker.patch("src.services.task_manager.StorageAgent")
    mock_storage.return_value.get.return_value = Task(id="1", title="Test")

    manager = TaskManager()
    task = manager.get_task("1")

    assert task.title == "Test"

def test_spy(mocker: MockerFixture) -> None:
    storage = InMemoryStorage()
    spy = mocker.spy(storage, "save")

    storage.save(Task(id="1", title="Test"))

    spy.assert_called_once()
```

## Dependency Injection Testing

### Constructor Injection (Preferred)

```python
# Production code
class TaskManager:
    def __init__(self, storage: StorageProtocol) -> None:
        self._storage = storage

# Test code - no mocking needed!
def test_task_manager() -> None:
    storage = InMemoryStorage()  # Use real implementation
    manager = TaskManager(storage=storage)

    task = manager.create_task("Test")

    assert storage.get(task.id) is not None
```

### Protocol-Based Mocking

```python
from typing import Protocol

class StorageProtocol(Protocol):
    def get(self, id: str) -> Task | None: ...
    def save(self, task: Task) -> None: ...

# Create mock that satisfies protocol
@pytest.fixture
def mock_storage() -> MagicMock:
    storage = MagicMock(spec=StorageProtocol)
    storage.get.return_value = None
    return storage

def test_with_typed_mock(mock_storage: MagicMock) -> None:
    manager = TaskManager(storage=mock_storage)
    # mock_storage only has methods from StorageProtocol
```

## Fake Implementations

```python
# Fake for testing - real behavior, in-memory
class FakeStorage:
    def __init__(self) -> None:
        self._data: dict[str, Task] = {}

    def get(self, id: str) -> Task | None:
        return self._data.get(id)

    def save(self, task: Task) -> None:
        self._data[task.id] = task

    def delete(self, id: str) -> bool:
        if id in self._data:
            del self._data[id]
            return True
        return False

@pytest.fixture
def fake_storage() -> FakeStorage:
    return FakeStorage()

def test_with_fake(fake_storage: FakeStorage) -> None:
    manager = TaskManager(storage=fake_storage)

    task = manager.create_task("Test")
    retrieved = manager.get_task(task.id)

    assert retrieved.title == "Test"
```

## Common Patterns

### Testing Exceptions

```python
def test_raises_on_not_found(mock_storage: MagicMock) -> None:
    mock_storage.get.return_value = None
    manager = TaskManager(storage=mock_storage)

    with pytest.raises(NotFoundError, match="Task .* not found"):
        manager.get_task("nonexistent")
```

### Testing Side Effects

```python
def test_save_called_on_create(mock_storage: MagicMock) -> None:
    manager = TaskManager(storage=mock_storage)

    task = manager.create_task("Test")

    mock_storage.save.assert_called_once()
    saved_task = mock_storage.save.call_args[0][0]
    assert saved_task.title == "Test"
```

### Resetting Mocks

```python
def test_multiple_operations(mock_storage: MagicMock) -> None:
    manager = TaskManager(storage=mock_storage)

    manager.get_task("1")
    mock_storage.get.assert_called_once()

    mock_storage.reset_mock()  # Clear call history

    manager.get_task("2")
    mock_storage.get.assert_called_once()  # Fresh count
```
