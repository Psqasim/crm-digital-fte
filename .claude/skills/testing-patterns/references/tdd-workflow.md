# TDD (Test-Driven Development) Workflow

## The Red-Green-Refactor Cycle

```
┌─────────────────────────────────────────────────────┐
│                                                     │
│    ┌───────┐     ┌───────┐     ┌──────────┐       │
│    │  RED  │────▶│ GREEN │────▶│ REFACTOR │       │
│    └───────┘     └───────┘     └──────────┘       │
│        ▲                            │              │
│        └────────────────────────────┘              │
│                                                     │
└─────────────────────────────────────────────────────┘
```

| Phase | Goal | Rules |
|-------|------|-------|
| **RED** | Write failing test | Test must fail for the right reason |
| **GREEN** | Make test pass | Write minimum code to pass |
| **REFACTOR** | Improve code | Tests must stay green |

## Phase 1: RED - Write Failing Test

### Write the Test First

```python
# tests/unit/test_task_manager.py
import pytest
from src.services.task_manager import TaskManager
from src.models.tasks import Task
from src.models.exceptions import ValidationError

class TestTaskManager:
    def test_create_task_with_valid_title(self) -> None:
        """Task should be created with given title."""
        manager = TaskManager()

        task = manager.create_task("Buy groceries")

        assert task.title == "Buy groceries"
        assert task.id is not None
        assert task.completed is False
```

### Run and Verify Failure

```bash
pytest tests/unit/test_task_manager.py -v
# Expected: ImportError or AttributeError (code doesn't exist yet)
```

### Key RED Phase Rules

1. **Test describes behavior, not implementation**
2. **Test should fail for the right reason** (missing code, not syntax error)
3. **One test at a time** - don't write multiple failing tests

## Phase 2: GREEN - Make Test Pass

### Write Minimum Code

```python
# src/services/task_manager.py
from uuid import uuid4
from src.models.tasks import Task

class TaskManager:
    def create_task(self, title: str) -> Task:
        return Task(
            id=str(uuid4()),
            title=title,
            completed=False,
        )
```

### Run and Verify Pass

```bash
pytest tests/unit/test_task_manager.py -v
# Expected: PASSED
```

### Key GREEN Phase Rules

1. **Write the simplest code that passes** - resist urge to add more
2. **Don't optimize yet** - that's for REFACTOR phase
3. **All tests must pass** - never leave tests failing

## Phase 3: REFACTOR - Improve Code

### Improve Without Changing Behavior

```python
# Add type hints, improve structure, extract methods
from uuid import uuid4
from dataclasses import dataclass
from src.models.tasks import Task

class TaskManager:
    def __init__(self, storage: StorageProtocol | None = None) -> None:
        self._storage = storage or InMemoryStorage()

    def create_task(self, title: str) -> Task:
        task = Task(
            id=self._generate_id(),
            title=title,
            completed=False,
        )
        self._storage.save(task)
        return task

    def _generate_id(self) -> str:
        return str(uuid4())
```

### Verify Tests Still Pass

```bash
pytest tests/unit/test_task_manager.py -v
# Expected: PASSED (same as before)
```

### Key REFACTOR Phase Rules

1. **Tests must stay green** - run after every change
2. **No new functionality** - only improve existing code
3. **Small steps** - commit frequently

## TDD Example: Complete Feature

### Iteration 1: Basic Creation

```python
# RED: Write test
def test_create_task_with_valid_title(self) -> None:
    manager = TaskManager()
    task = manager.create_task("Buy groceries")
    assert task.title == "Buy groceries"

# GREEN: Implement
def create_task(self, title: str) -> Task:
    return Task(id=str(uuid4()), title=title, completed=False)

# REFACTOR: (nothing needed yet)
```

### Iteration 2: Validation

```python
# RED: Write test for validation
def test_create_task_raises_on_empty_title(self) -> None:
    manager = TaskManager()
    with pytest.raises(ValidationError, match="Title cannot be empty"):
        manager.create_task("")

# GREEN: Add validation
def create_task(self, title: str) -> Task:
    if not title.strip():
        raise ValidationError("Title cannot be empty")
    return Task(id=str(uuid4()), title=title, completed=False)

# REFACTOR: Extract validation
def create_task(self, title: str) -> Task:
    self._validate_title(title)
    return Task(id=str(uuid4()), title=title, completed=False)

def _validate_title(self, title: str) -> None:
    if not title.strip():
        raise ValidationError("Title cannot be empty")
```

### Iteration 3: Storage Integration

```python
# RED: Write test for persistence
def test_created_task_is_persisted(self, storage: FakeStorage) -> None:
    manager = TaskManager(storage=storage)
    task = manager.create_task("Test")
    assert storage.get(task.id) is not None

# GREEN: Add storage
def create_task(self, title: str) -> Task:
    self._validate_title(title)
    task = Task(id=str(uuid4()), title=title, completed=False)
    self._storage.save(task)
    return task

# REFACTOR: Dependency injection pattern
class TaskManager:
    def __init__(self, storage: StorageProtocol) -> None:
        self._storage = storage
```

## Test Organization for TDD

### Test Naming Convention

```python
def test_<method>_<scenario>_<expected_outcome>() -> None:
    """Descriptive test names document behavior."""
    pass

# Examples:
def test_create_task_with_valid_title_returns_task() -> None: ...
def test_create_task_with_empty_title_raises_validation_error() -> None: ...
def test_complete_task_with_valid_id_marks_completed() -> None: ...
def test_complete_task_with_invalid_id_raises_not_found() -> None: ...
```

### Test Structure: Arrange-Act-Assert

```python
def test_complete_task_marks_as_done(self) -> None:
    # Arrange: Set up preconditions
    storage = FakeStorage()
    manager = TaskManager(storage=storage)
    task = manager.create_task("Test")

    # Act: Execute the behavior
    completed_task = manager.complete_task(task.id)

    # Assert: Verify outcomes
    assert completed_task.completed is True
    assert storage.get(task.id).completed is True
```

## TDD Best Practices

### Start with the Happy Path

```python
# First test: normal successful case
def test_create_task_success(self) -> None:
    task = manager.create_task("Valid title")
    assert task.title == "Valid title"

# Then add edge cases
def test_create_task_empty_title(self) -> None: ...
def test_create_task_whitespace_only(self) -> None: ...
def test_create_task_max_length(self) -> None: ...
```

### Test Behavior, Not Implementation

```python
# BAD: Tests implementation details
def test_uses_uuid4_for_id(self) -> None:
    with patch("uuid.uuid4") as mock_uuid:
        mock_uuid.return_value = "123"
        task = manager.create_task("Test")
        mock_uuid.assert_called_once()

# GOOD: Tests behavior
def test_task_id_is_unique(self) -> None:
    task1 = manager.create_task("First")
    task2 = manager.create_task("Second")
    assert task1.id != task2.id
```

### One Assertion Per Test (Generally)

```python
# Okay: Related assertions about single behavior
def test_create_task_returns_correct_task(self) -> None:
    task = manager.create_task("Test")
    assert task.title == "Test"
    assert task.completed is False
    assert task.id is not None

# Better for complex scenarios: separate tests
def test_create_task_has_correct_title(self) -> None:
    task = manager.create_task("Test")
    assert task.title == "Test"

def test_create_task_is_not_completed(self) -> None:
    task = manager.create_task("Test")
    assert task.completed is False
```

## When to Write Tests First

| Scenario | TDD? | Reason |
|----------|------|--------|
| New feature | Yes | Drives design |
| Bug fix | Yes | Reproduces bug first |
| Refactoring | No | Tests exist already |
| Exploratory code | No | Design unclear |
| Learning new API | No | Spike first |

## Common TDD Pitfalls

### Writing Too Much Code

```python
# WRONG: Implementing everything at once
def create_task(self, title: str, description: str = "",
                due_date: datetime = None, priority: int = 0) -> Task:
    # All the features at once...

# RIGHT: One test, one feature at a time
def create_task(self, title: str) -> Task:
    return Task(id=str(uuid4()), title=title, completed=False)
# Add description in next iteration after test is written
```

### Skipping the RED Phase

Always see the test fail first. A test that never fails proves nothing.

```bash
# Always run and see failure before implementing
pytest tests/unit/test_new_feature.py -v
# FAILED - Good! Now implement.
```
