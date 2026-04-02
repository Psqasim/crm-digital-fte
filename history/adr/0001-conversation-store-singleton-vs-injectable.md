# ADR-0001: ConversationStore Lifecycle — Singleton vs. Injectable Dependency

- **Status:** Accepted
- **Date:** 2026-04-02
- **Feature:** 002-memory-state (Phase 2C — Memory & State)
- **Context:** Phase 2C introduces `ConversationStore` as the single source of truth for all in-memory agent state: customer profiles, conversation histories, sentiment trends, ticket statuses, and cross-channel identity maps. The store must be accessed by `process_ticket()` on every call, must be test-isolatable, and must be replaceable in Phase 4A when the backing store migrates from in-memory dicts to Neon PostgreSQL + pgvector. Two viable instantiation strategies were evaluated before implementation began.

## Decision

**Chosen approach: Module-level singleton with a `get_store()` factory function, but `ConversationStore` is also directly instantiable (no private constructor) for test isolation.**

Concretely:
- `src/agent/conversation_store.py` exports a module-level `_store: ConversationStore | None = None` and a `get_store() -> ConversationStore` factory that lazily initialises it.
- `process_ticket()` calls `get_store()` at the top of the function body — one line, no import-time side effects.
- Unit tests construct `ConversationStore()` directly (fresh instance per test) — they never call `get_store()`.
- Integration tests may call `get_store()` or pass an instance explicitly.
- In Phase 4A, `get_store()` is the single swap point: return a `PostgresConversationStore` that satisfies the same interface (`contracts/store_interface.py`).

```python
# src/agent/conversation_store.py
_store: ConversationStore | None = None

def get_store() -> ConversationStore:
    global _store
    if _store is None:
        _store = ConversationStore()
    return _store
```

```python
# src/agent/prototype.py — usage
from src.agent.conversation_store import get_store

def process_ticket(msg: TicketMessage) -> AgentResponse:
    store = get_store()
    ...
```

```python
# tests/unit/test_conversation_store.py — test isolation
def test_message_cap():
    store = ConversationStore()   # fresh — not the singleton
    ...
```

## Consequences

### Positive

- **Zero import-time side effects**: the store is initialised only on first `get_store()` call, not at module import. Tests that import `prototype.py` without calling `process_ticket` are unaffected.
- **Test isolation without mocking**: each unit test creates `ConversationStore()` directly — no `monkeypatch`, no `mock.patch`, no fixture teardown complexity. The 16 Phase 2B tests are completely unaffected because they stub at the `evaluate_escalation` / `_kb.search` level and never invoke `get_store()`.
- **Single swap point for Phase 4A**: `get_store()` is the only location that needs to change when migrating to PostgreSQL. The rest of `prototype.py` is untouched.
- **Explicit, auditable**: the singleton pattern is visible in one function; no framework magic (no DI container, no `@inject` decorator).
- **Minimal diff**: the change to `prototype.py` is a single `store = get_store()` line at the top of `process_ticket` — all other lines below remain identical in structure.

### Negative

- **Global mutable state risk**: the singleton is process-global. If a test accidentally calls `get_store()` (instead of `ConversationStore()`), it pollutes state across tests. Mitigation: document the rule explicitly in `quickstart.md`; add a `reset_store()` helper for integration test teardown.
- **Not async-safe**: the lazy initialisation pattern is not thread-safe. For this phase (single-process, synchronous prototype) this is acceptable. Phase 4 will introduce async FastAPI workers — at that point the singleton must be replaced with a request-scoped dependency (FastAPI `Depends()`).
- **Implicit coupling**: `process_ticket` has an implicit dependency on the module-level singleton rather than an explicit parameter. This makes the dependency invisible to callers and violates strict dependency-injection discipline. Accepted as a deliberate tradeoff for prototype simplicity.
- **Phase 4A migration requires interface discipline**: swapping `get_store()` to return a PostgreSQL-backed store only works if `conversation_store.py` strictly implements the interface in `contracts/store_interface.py`. Any drift between implementation and contract will be caught at migration time, not earlier. Mitigation: the contract stub is the authoritative reference; all 13 method signatures must be preserved exactly.

## Alternatives Considered

### Alternative A: Explicit Dependency Injection (pass store as parameter)

```python
def process_ticket(msg: TicketMessage, store: ConversationStore | None = None) -> AgentResponse:
    if store is None:
        store = get_store()
```

- **Pro**: Makes the dependency explicit; trivial to pass a test instance; matches production FastAPI `Depends()` pattern.
- **Con**: Changes the public signature of `process_ticket`, which is imported and called in all 16 Phase 2B tests. Updating every test call site is unnecessary churn at this prototype stage. The `| None = None` default also hides the coupling rather than resolving it.
- **Verdict**: Rejected for Phase 2C. **Scheduled for Phase 4A** when FastAPI `Depends()` will replace the singleton cleanly.

### Alternative B: Class-level singleton (metaclass or `__new__` override)

```python
class ConversationStore:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```

- **Pro**: `ConversationStore()` always returns the same instance — no separate factory function needed.
- **Con**: Breaks test isolation completely — there is no way to create a fresh instance without `ConversationStore._instance = None` hacks. Violates the "directly instantiable for tests" requirement.
- **Verdict**: Rejected. Test isolation is a hard requirement (SC-007).

### Alternative C: Framework DI container (e.g., `dependency_injector` or `lagom`)

- **Pro**: Elegant for large applications; scoped lifecycles (singleton, request, transient).
- **Con**: Introduces a new dependency with significant learning curve; overkill for a two-module prototype. Phase 4A already plans FastAPI `Depends()` which provides built-in DI without an extra library.
- **Verdict**: Rejected for all prototype phases. Revisit only if the system grows beyond FastAPI.

## References

- Feature Spec: `specs/002-memory-state/spec.md`
- Implementation Plan: `specs/002-memory-state/plan.md`
- API Contract: `specs/002-memory-state/contracts/store_interface.py`
- Data Model: `specs/002-memory-state/data-model.md`
- Integration Guide: `specs/002-memory-state/quickstart.md`
- Related ADRs: None (first ADR in this project)
- Phase 4A migration target: FastAPI `Depends()` pattern (to be captured in a new ADR when Phase 4 planning begins)
