# Integration Testing

## Overview

Integration tests verify that multiple components work together correctly. They sit between unit tests (isolated) and end-to-end tests (full system).

```
┌────────────────────────────────────────────────────────┐
│                    Test Pyramid                        │
│                                                        │
│                      /\        E2E (few)               │
│                     /  \       - Full system           │
│                    /────\                              │
│                   /      \     Integration (some)      │
│                  / Integ  \    - Multiple components   │
│                 /──────────\                           │
│                /            \  Unit (many)             │
│               /    Unit      \ - Single component      │
│              /________________\                        │
│                                                        │
└────────────────────────────────────────────────────────┘
```

## Integration Test Categories

| Category | Scope | Example |
|----------|-------|---------|
| **Component** | 2-3 classes | TaskManager + Storage |
| **Workflow** | Complete user flow | Create → Update → Complete |
| **Contract** | Interface compliance | Agent implements BaseAgent |
| **Layer** | Adjacent layers | Service → Repository |

## Project Structure

```
tests/
├── unit/                    # Isolated tests with mocks
│   ├── test_task_manager.py
│   └── test_storage.py
├── integration/             # Multi-component tests
│   ├── conftest.py          # Real implementations
│   ├── test_task_workflow.py
│   └── test_agent_integration.py
└── contract/                # Interface compliance
    └── test_agent_contracts.py
```

## Integration Test Fixtures

### Real Implementations

```python
# tests/integration/conftest.py
import pytest
from src.agents.orchestrator import OrchestratorAgent
from src.agents.task_manager import TaskManagerAgent
from src.agents.storage import StorageAgent
from src.backends.memory import InMemoryBackend

@pytest.fixture
def storage_backend() -> InMemoryBackend:
    """Real in-memory storage for integration tests."""
    return InMemoryBackend()

@pytest.fixture
def storage_agent(storage_backend: InMemoryBackend) -> StorageAgent:
    """Real storage agent with in-memory backend."""
    return StorageAgent(backend=storage_backend)

@pytest.fixture
def task_manager(storage_agent: StorageAgent) -> TaskManagerAgent:
    """Real task manager with real storage."""
    return TaskManagerAgent(storage=storage_agent)

@pytest.fixture
def orchestrator(
    task_manager: TaskManagerAgent,
    storage_agent: StorageAgent,
) -> OrchestratorAgent:
    """Full orchestrator with all agents."""
    return OrchestratorAgent(
        agents={
            "task": task_manager,
            "storage": storage_agent,
        }
    )
```

### Fixture Scope for Expensive Setup

```python
@pytest.fixture(scope="module")
def database_connection() -> Generator[Connection, None, None]:
    """Shared database connection for module."""
    conn = create_test_database()
    yield conn
    conn.close()
    cleanup_test_database()

@pytest.fixture
def clean_tables(database_connection: Connection) -> Generator[None, None, None]:
    """Reset tables before each test."""
    yield
    database_connection.execute("DELETE FROM tasks")
    database_connection.commit()
```

## Workflow Testing

### Complete User Flow

```python
# tests/integration/test_task_workflow.py
import pytest
from src.agents.orchestrator import OrchestratorAgent

class TestTaskWorkflow:
    """Test complete task management workflow."""

    def test_full_task_lifecycle(self, orchestrator: OrchestratorAgent) -> None:
        """Create, update, complete, and delete a task."""
        # Create
        create_response = orchestrator.handle_message(
            AgentMessage(action="task_add", payload={"title": "Buy groceries"})
        )
        assert create_response.success
        task_id = create_response.data["id"]

        # Update
        update_response = orchestrator.handle_message(
            AgentMessage(
                action="task_update",
                payload={"id": task_id, "title": "Buy organic groceries"},
            )
        )
        assert update_response.success

        # Complete
        complete_response = orchestrator.handle_message(
            AgentMessage(action="task_complete", payload={"id": task_id})
        )
        assert complete_response.success
        assert complete_response.data["completed"] is True

        # Verify state
        get_response = orchestrator.handle_message(
            AgentMessage(action="task_get", payload={"id": task_id})
        )
        assert get_response.data["title"] == "Buy organic groceries"
        assert get_response.data["completed"] is True

    def test_task_list_reflects_changes(
        self, orchestrator: OrchestratorAgent
    ) -> None:
        """Verify list updates after operations."""
        # Create multiple tasks
        for title in ["Task 1", "Task 2", "Task 3"]:
            orchestrator.handle_message(
                AgentMessage(action="task_add", payload={"title": title})
            )

        # List all
        response = orchestrator.handle_message(
            AgentMessage(action="task_list", payload={})
        )
        assert len(response.data["tasks"]) == 3

        # Complete one
        task_id = response.data["tasks"][0]["id"]
        orchestrator.handle_message(
            AgentMessage(action="task_complete", payload={"id": task_id})
        )

        # List completed
        response = orchestrator.handle_message(
            AgentMessage(
                action="task_list",
                payload={"filter": {"completed": True}},
            )
        )
        assert len(response.data["tasks"]) == 1
```

### Error Propagation

```python
class TestErrorHandling:
    """Verify errors propagate correctly through layers."""

    def test_not_found_error_propagates(
        self, orchestrator: OrchestratorAgent
    ) -> None:
        """NotFoundError should propagate from storage to orchestrator."""
        response = orchestrator.handle_message(
            AgentMessage(action="task_get", payload={"id": "nonexistent"})
        )

        assert response.success is False
        assert response.error_code == "NOT_FOUND"
        assert "not found" in response.error_message.lower()

    def test_validation_error_propagates(
        self, orchestrator: OrchestratorAgent
    ) -> None:
        """ValidationError should be caught and formatted."""
        response = orchestrator.handle_message(
            AgentMessage(action="task_add", payload={"title": ""})
        )

        assert response.success is False
        assert response.error_code == "VALIDATION_ERROR"
```

## Contract Testing

### Protocol Compliance

```python
# tests/contract/test_agent_contracts.py
import pytest
from typing import Protocol
from src.agents.base import BaseAgent
from src.agents.task_manager import TaskManagerAgent
from src.agents.storage import StorageAgent
from src.models.messages import AgentMessage, AgentResponse

class TestBaseAgentContract:
    """Verify all agents implement BaseAgent correctly."""

    @pytest.fixture(params=[TaskManagerAgent, StorageAgent])
    def agent_class(self, request: pytest.FixtureRequest) -> type[BaseAgent]:
        return request.param

    def test_has_handle_message(self, agent_class: type[BaseAgent]) -> None:
        """All agents must implement handle_message."""
        assert hasattr(agent_class, "handle_message")
        assert callable(getattr(agent_class, "handle_message"))

    def test_handle_message_returns_response(
        self, agent_class: type[BaseAgent]
    ) -> None:
        """handle_message must return AgentResponse."""
        agent = self._create_agent(agent_class)
        message = AgentMessage(action="unknown", payload={})

        result = agent.handle_message(message)

        assert isinstance(result, AgentResponse)

    def test_unknown_action_returns_error(
        self, agent_class: type[BaseAgent]
    ) -> None:
        """Unknown actions should return error, not raise."""
        agent = self._create_agent(agent_class)
        message = AgentMessage(action="definitely_unknown_action", payload={})

        result = agent.handle_message(message)

        assert result.success is False

    def _create_agent(self, agent_class: type[BaseAgent]) -> BaseAgent:
        """Factory for creating agents with dependencies."""
        if agent_class == TaskManagerAgent:
            return TaskManagerAgent(storage=InMemoryStorage())
        elif agent_class == StorageAgent:
            return StorageAgent(backend=InMemoryBackend())
        raise ValueError(f"Unknown agent class: {agent_class}")
```

### Response Format Contract

```python
class TestResponseContract:
    """Verify response format consistency."""

    def test_success_response_format(self, task_manager: TaskManagerAgent) -> None:
        """Success responses have required fields."""
        response = task_manager.handle_message(
            AgentMessage(action="task_add", payload={"title": "Test"})
        )

        assert response.success is True
        assert response.data is not None
        assert response.error_code is None
        assert response.error_message is None

    def test_error_response_format(self, task_manager: TaskManagerAgent) -> None:
        """Error responses have required fields."""
        response = task_manager.handle_message(
            AgentMessage(action="task_get", payload={"id": "nonexistent"})
        )

        assert response.success is False
        assert response.error_code is not None
        assert response.error_message is not None
```

## Component Integration

### Layer Integration

```python
class TestServiceRepositoryIntegration:
    """Test service layer with real repository."""

    def test_service_persists_through_repository(
        self,
        task_manager: TaskManagerAgent,
        storage_agent: StorageAgent,
    ) -> None:
        """Verify data flows from service to storage."""
        # Create through task manager
        response = task_manager.handle_message(
            AgentMessage(action="task_add", payload={"title": "Test"})
        )
        task_id = response.data["id"]

        # Verify in storage directly
        storage_response = storage_agent.handle_message(
            AgentMessage(action="storage_get", payload={"id": task_id})
        )

        assert storage_response.success
        assert storage_response.data["title"] == "Test"
```

### Cross-Agent Communication

```python
class TestAgentCommunication:
    """Test agents communicate correctly."""

    def test_orchestrator_routes_to_task_manager(
        self,
        orchestrator: OrchestratorAgent,
    ) -> None:
        """Orchestrator correctly routes task_* to TaskManager."""
        response = orchestrator.handle_message(
            AgentMessage(action="task_add", payload={"title": "Test"})
        )

        assert response.success
        assert response.source_agent == "task_manager"

    def test_orchestrator_routes_to_storage(
        self,
        orchestrator: OrchestratorAgent,
    ) -> None:
        """Orchestrator correctly routes storage_* to StorageAgent."""
        response = orchestrator.handle_message(
            AgentMessage(action="storage_list", payload={})
        )

        assert response.success
        assert response.source_agent == "storage"
```

## Best Practices

### Isolation Between Tests

```python
@pytest.fixture(autouse=True)
def reset_storage(storage_backend: InMemoryBackend) -> Generator[None, None, None]:
    """Clear storage after each test."""
    yield
    storage_backend.clear()
```

### Test Data Builders

```python
class TaskBuilder:
    """Builder for test tasks with sensible defaults."""

    def __init__(self) -> None:
        self._title = "Test Task"
        self._completed = False

    def with_title(self, title: str) -> "TaskBuilder":
        self._title = title
        return self

    def completed(self) -> "TaskBuilder":
        self._completed = True
        return self

    def build_message(self) -> AgentMessage:
        return AgentMessage(
            action="task_add",
            payload={"title": self._title, "completed": self._completed},
        )

# Usage
def test_with_builder(orchestrator: OrchestratorAgent) -> None:
    message = TaskBuilder().with_title("Custom").completed().build_message()
    response = orchestrator.handle_message(message)
    assert response.success
```

### Markers for Test Selection

```python
# conftest.py
def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "integration: integration tests")
    config.addinivalue_line("markers", "slow: slow running tests")

# tests/integration/test_workflow.py
@pytest.mark.integration
class TestWorkflow:
    @pytest.mark.slow
    def test_large_dataset(self) -> None:
        pass
```

```bash
# Run only integration tests
pytest -m integration

# Skip slow tests
pytest -m "integration and not slow"
```
