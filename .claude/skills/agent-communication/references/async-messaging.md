# Async Message Passing

## Overview

Async messaging enables non-blocking communication between agents, essential for:
- High throughput systems
- Long-running operations
- Distributed architectures
- Event-driven patterns

## Async Agent Interface

### Base Async Agent

```python
from abc import ABC, abstractmethod
from typing import Protocol

class AsyncAgentProtocol(Protocol):
    """Protocol for async agents."""

    async def handle_message(self, message: AgentMessage) -> AgentResponse: ...
    async def start(self) -> None: ...
    async def shutdown(self) -> None: ...

class BaseAsyncAgent(ABC):
    """Base class for async agents."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._running = False

    @abstractmethod
    async def handle_message(self, message: AgentMessage) -> AgentResponse:
        """Process message asynchronously."""
        pass

    async def start(self) -> None:
        """Initialize agent resources."""
        self._running = True

    async def shutdown(self) -> None:
        """Clean up agent resources."""
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running
```

### Async Task Manager

```python
class AsyncTaskManagerAgent(BaseAsyncAgent):
    """Async task management agent."""

    def __init__(self, storage: AsyncStorageProtocol) -> None:
        super().__init__("task_manager")
        self._storage = storage
        self._handlers: dict[str, Callable] = {
            "task_add": self._add_task,
            "task_get": self._get_task,
            "task_list": self._list_tasks,
            "task_complete": self._complete_task,
        }

    async def handle_message(self, message: AgentMessage) -> AgentResponse:
        handler = self._handlers.get(message.action)
        if not handler:
            return AgentResponse.error(
                "UNKNOWN_ACTION",
                f"Unknown action: {message.action}",
            )

        try:
            return await handler(message.payload)
        except AgentError as e:
            return e.to_response(message.correlation_id)

    async def _add_task(self, payload: dict) -> AgentResponse:
        task = Task(
            id=str(uuid4()),
            title=payload["title"],
            completed=False,
        )
        await self._storage.save(task)
        return AgentResponse.ok({"id": task.id, "title": task.title})

    async def _get_task(self, payload: dict) -> AgentResponse:
        task = await self._storage.get(payload["id"])
        if not task:
            raise NotFoundError("Task", payload["id"])
        return AgentResponse.ok(task.model_dump())
```

## Queue-Based Communication

### In-Memory Async Queue

```python
import asyncio
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")

@dataclass
class QueueMessage(Generic[T]):
    """Wrapper for queued messages."""
    payload: T
    timestamp: datetime = field(default_factory=datetime.utcnow)
    priority: int = 0

class AsyncMessageQueue(Generic[T]):
    """Priority-based async message queue."""

    def __init__(self, maxsize: int = 0) -> None:
        self._queue: asyncio.PriorityQueue[tuple[int, QueueMessage[T]]] = (
            asyncio.PriorityQueue(maxsize=maxsize)
        )
        self._counter = 0  # For FIFO within same priority

    async def put(self, message: T, priority: int = 0) -> None:
        """Add message to queue."""
        wrapped = QueueMessage(payload=message, priority=priority)
        # Negate priority so higher = more important
        await self._queue.put((-priority, self._counter, wrapped))
        self._counter += 1

    async def get(self) -> T:
        """Get next message from queue."""
        _, _, wrapped = await self._queue.get()
        return wrapped.payload

    def task_done(self) -> None:
        """Mark current task as done."""
        self._queue.task_done()

    async def join(self) -> None:
        """Wait for all tasks to complete."""
        await self._queue.join()

    @property
    def qsize(self) -> int:
        return self._queue.qsize()

    @property
    def empty(self) -> bool:
        return self._queue.empty()
```

### Request-Response with Queues

```python
@dataclass
class PendingRequest:
    """Tracks pending request for response matching."""
    message: AgentMessage
    future: asyncio.Future[AgentResponse]
    created_at: datetime = field(default_factory=datetime.utcnow)

class QueuedOrchestrator:
    """Orchestrator using request/response queues."""

    def __init__(self) -> None:
        self._request_queue: AsyncMessageQueue[AgentMessage] = AsyncMessageQueue()
        self._response_queue: AsyncMessageQueue[AgentResponse] = AsyncMessageQueue()
        self._pending: dict[str, PendingRequest] = {}
        self._workers: list[asyncio.Task] = []

    async def start(self, num_workers: int = 3) -> None:
        """Start worker tasks."""
        for i in range(num_workers):
            worker = asyncio.create_task(self._process_requests())
            self._workers.append(worker)

        # Start response handler
        self._workers.append(asyncio.create_task(self._handle_responses()))

    async def shutdown(self) -> None:
        """Graceful shutdown."""
        # Wait for queues to drain
        await self._request_queue.join()

        # Cancel workers
        for worker in self._workers:
            worker.cancel()

        await asyncio.gather(*self._workers, return_exceptions=True)

    async def send(self, message: AgentMessage) -> AgentResponse:
        """Send message and wait for response."""
        future: asyncio.Future[AgentResponse] = asyncio.get_event_loop().create_future()

        self._pending[message.id] = PendingRequest(
            message=message,
            future=future,
        )

        await self._request_queue.put(message, priority=message.priority.value)

        try:
            return await asyncio.wait_for(future, timeout=30.0)
        except asyncio.TimeoutError:
            self._pending.pop(message.id, None)
            return AgentResponse.error(
                "TIMEOUT",
                f"Request timed out: {message.action}",
            )

    async def _process_requests(self) -> None:
        """Worker that processes requests."""
        while True:
            try:
                message = await self._request_queue.get()
                response = await self._route_and_handle(message)
                await self._response_queue.put(response)
                self._request_queue.task_done()
            except asyncio.CancelledError:
                break

    async def _handle_responses(self) -> None:
        """Match responses to pending requests."""
        while True:
            try:
                response = await self._response_queue.get()
                pending = self._pending.pop(response.correlation_id, None)
                if pending and not pending.future.done():
                    pending.future.set_result(response)
                self._response_queue.task_done()
            except asyncio.CancelledError:
                break
```

## Pub/Sub Pattern

### Event Bus

```python
from collections import defaultdict
from typing import Callable, Awaitable

EventHandler = Callable[[AgentMessage], Awaitable[None]]

class EventBus:
    """Async event bus for pub/sub communication."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Subscribe to event type."""
        self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Unsubscribe from event type."""
        if handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)

    async def publish(self, event_type: str, message: AgentMessage) -> None:
        """Publish event to all subscribers."""
        handlers = self._subscribers.get(event_type, [])
        if handlers:
            await asyncio.gather(
                *(handler(message) for handler in handlers),
                return_exceptions=True,
            )

    async def publish_and_wait(
        self,
        event_type: str,
        message: AgentMessage,
    ) -> list[AgentResponse]:
        """Publish and collect responses."""
        handlers = self._subscribers.get(event_type, [])
        results = await asyncio.gather(
            *(handler(message) for handler in handlers),
            return_exceptions=True,
        )
        return [r for r in results if isinstance(r, AgentResponse)]

# Usage
bus = EventBus()

# Subscribe agents
bus.subscribe("task_created", audit_agent.on_task_created)
bus.subscribe("task_created", notification_agent.on_task_created)

# Publish event
await bus.publish("task_created", AgentMessage(
    action="task_created",
    payload={"task_id": "123", "title": "New task"},
))
```

## Async Patterns

### Concurrent Agent Calls

```python
async def process_batch(
    orchestrator: AsyncOrchestrator,
    messages: list[AgentMessage],
) -> list[AgentResponse]:
    """Process multiple messages concurrently."""
    return await asyncio.gather(
        *(orchestrator.handle_message(msg) for msg in messages)
    )

# With semaphore for rate limiting
async def process_with_limit(
    orchestrator: AsyncOrchestrator,
    messages: list[AgentMessage],
    max_concurrent: int = 10,
) -> list[AgentResponse]:
    """Process with concurrency limit."""
    semaphore = asyncio.Semaphore(max_concurrent)

    async def limited_handle(msg: AgentMessage) -> AgentResponse:
        async with semaphore:
            return await orchestrator.handle_message(msg)

    return await asyncio.gather(
        *(limited_handle(msg) for msg in messages)
    )
```

### Timeout Handling

```python
async def handle_with_timeout(
    agent: AsyncAgentProtocol,
    message: AgentMessage,
    timeout_seconds: float = 5.0,
) -> AgentResponse:
    """Handle message with timeout."""
    try:
        async with asyncio.timeout(timeout_seconds):
            return await agent.handle_message(message)
    except asyncio.TimeoutError:
        return AgentResponse.error(
            "TIMEOUT",
            f"Agent timed out after {timeout_seconds}s",
            correlation_id=message.correlation_id,
        )
```

### Graceful Shutdown

```python
class AsyncOrchestrator:
    """Orchestrator with graceful shutdown."""

    def __init__(self) -> None:
        self._agents: dict[str, BaseAsyncAgent] = {}
        self._shutdown_event = asyncio.Event()

    async def start(self) -> None:
        """Start all agents."""
        await asyncio.gather(
            *(agent.start() for agent in self._agents.values())
        )

    async def shutdown(self, timeout: float = 30.0) -> None:
        """Graceful shutdown with timeout."""
        self._shutdown_event.set()

        # Give agents time to finish current work
        shutdown_tasks = [
            asyncio.create_task(agent.shutdown())
            for agent in self._agents.values()
        ]

        try:
            await asyncio.wait_for(
                asyncio.gather(*shutdown_tasks),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            logger.warning("Shutdown timeout, forcing termination")
            for task in shutdown_tasks:
                task.cancel()

    async def handle_message(self, message: AgentMessage) -> AgentResponse:
        if self._shutdown_event.is_set():
            return AgentResponse.error(
                "SHUTTING_DOWN",
                "System is shutting down",
            )
        # Normal processing
```

## Best Practices

### 1. Always Use Timeouts

```python
# Every async call should have a timeout
async with asyncio.timeout(5.0):
    response = await agent.handle_message(message)
```

### 2. Handle Cancellation

```python
async def long_running_task(self) -> None:
    try:
        while True:
            await self._process_next()
    except asyncio.CancelledError:
        # Clean up resources
        await self._cleanup()
        raise  # Re-raise to signal cancellation
```

### 3. Use TaskGroups for Concurrent Work

```python
async def process_all(self, messages: list[AgentMessage]) -> list[AgentResponse]:
    results: list[AgentResponse] = []

    async with asyncio.TaskGroup() as tg:
        for msg in messages:
            tg.create_task(self._process_and_collect(msg, results))

    return results
```
