# Pytest Setup and Configuration

## pyproject.toml Configuration

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "-v",
    "--strict-markers",
    "--strict-config",
    "-ra",
]
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests as integration tests",
    "unit: marks tests as unit tests",
]
filterwarnings = [
    "error",
    "ignore::DeprecationWarning",
]
asyncio_mode = "auto"
```

## Markers

### Built-in Markers

```python
import pytest

@pytest.mark.skip(reason="Not implemented yet")
def test_future_feature() -> None:
    pass

@pytest.mark.skipif(sys.platform == "win32", reason="Unix only")
def test_unix_specific() -> None:
    pass

@pytest.mark.xfail(reason="Known bug #123")
def test_known_failure() -> None:
    assert False

@pytest.mark.parametrize("input,expected", [
    ("hello", 5),
    ("world", 5),
    ("", 0),
])
def test_string_length(input: str, expected: int) -> None:
    assert len(input) == expected
```

### Custom Markers

```python
# conftest.py
import pytest

def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "integration: integration tests")

# Usage
@pytest.mark.slow
def test_performance() -> None:
    pass

@pytest.mark.integration
def test_database_connection() -> None:
    pass
```

Run specific markers:
```bash
pytest -m "not slow"           # Skip slow tests
pytest -m "unit"               # Only unit tests
pytest -m "integration"        # Only integration tests
```

## Fixtures

### Scope Levels

```python
@pytest.fixture(scope="function")  # Default: new for each test
def fresh_storage() -> InMemoryStorage:
    return InMemoryStorage()

@pytest.fixture(scope="class")  # Shared across class
def shared_client() -> APIClient:
    return APIClient()

@pytest.fixture(scope="module")  # Shared across module
def database_connection() -> Connection:
    conn = create_connection()
    yield conn
    conn.close()

@pytest.fixture(scope="session")  # Shared across entire session
def expensive_resource() -> Resource:
    return load_expensive_resource()
```

### Fixture Finalization

```python
@pytest.fixture
def temp_file() -> Generator[Path, None, None]:
    """Use yield for cleanup."""
    path = Path("/tmp/test_file.txt")
    path.write_text("test content")
    yield path
    path.unlink()  # Cleanup after test

@pytest.fixture
def database(request: pytest.FixtureRequest) -> Database:
    """Use finalizer for complex cleanup."""
    db = Database()
    db.connect()

    def cleanup() -> None:
        db.rollback()
        db.disconnect()

    request.addfinalizer(cleanup)
    return db
```

### Fixture Factories

```python
@pytest.fixture
def make_task() -> Callable[..., Task]:
    """Factory fixture for creating test tasks."""
    created_tasks: list[Task] = []

    def _make_task(
        title: str = "Test Task",
        completed: bool = False,
    ) -> Task:
        task = Task(title=title, completed=completed)
        created_tasks.append(task)
        return task

    return _make_task

def test_multiple_tasks(make_task: Callable[..., Task]) -> None:
    task1 = make_task("First")
    task2 = make_task("Second", completed=True)
    assert task1.title != task2.title
```

### Autouse Fixtures

```python
@pytest.fixture(autouse=True)
def reset_singletons() -> Generator[None, None, None]:
    """Automatically reset singletons before each test."""
    yield
    SingletonClass.reset()

@pytest.fixture(autouse=True, scope="session")
def configure_logging() -> None:
    """Configure logging once for entire test session."""
    logging.basicConfig(level=logging.DEBUG)
```

## conftest.py Hierarchy

```
tests/
├── conftest.py              # Session/global fixtures
│   └── @pytest.fixture(scope="session")
│       def api_client(): ...
├── unit/
│   ├── conftest.py          # Unit test fixtures
│   │   └── @pytest.fixture
│   │       def mock_storage(): ...
│   └── test_services.py
└── integration/
    ├── conftest.py          # Integration fixtures
    │   └── @pytest.fixture
    │       def database(): ...
    └── test_workflows.py
```

## CLI Options

```bash
# Basic execution
pytest                        # Run all tests
pytest tests/unit/            # Run specific directory
pytest tests/test_app.py      # Run specific file
pytest tests/test_app.py::test_create  # Run specific test

# Output control
pytest -v                     # Verbose output
pytest -vv                    # More verbose
pytest -q                     # Quiet mode
pytest --tb=short             # Shorter tracebacks
pytest --tb=no                # No tracebacks

# Selection
pytest -k "create"            # Tests matching "create"
pytest -k "create and not delete"  # Boolean expressions
pytest -m slow                # Tests with marker
pytest --last-failed          # Re-run failures only
pytest --failed-first         # Run failures first

# Debugging
pytest -x                     # Stop on first failure
pytest --maxfail=3            # Stop after 3 failures
pytest -s                     # Show print statements
pytest --pdb                  # Drop into debugger on failure

# Performance
pytest -n auto                # Parallel execution (pytest-xdist)
pytest --durations=10         # Show 10 slowest tests
```
