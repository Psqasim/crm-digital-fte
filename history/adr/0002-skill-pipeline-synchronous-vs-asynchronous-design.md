# ADR-0002: Skill Pipeline — Synchronous Sequential Design (Phase 2E) with Async Migration Path (Phase 4)

- **Status:** Accepted
- **Date:** 2026-04-03
- **Feature:** 003-mcp-server (Phase 2E — Agent Skills)
- **Context:** Phase 2E introduces a `SkillsInvoker` that orchestrates 5 agent skills in mandatory order (Customer Identification → Sentiment Analysis → Knowledge Retrieval → Escalation Decision → Channel Adaptation) for every incoming message. The invoker wraps existing synchronous functions (`resolve_identity`, `compute_sentiment_trend`, `KnowledgeBase.search`, `evaluate_escalation`, `format_response`) without breaking the current single-process synchronous prototype or any of the 79 existing passing tests. Phase 4 will introduce async FastAPI workers, Apache Kafka consumption via `aiokafka`, and Neon PostgreSQL via `asyncpg` — all requiring `async/await` throughout the call stack. The decision: how to design the invoker now so it is correct for Phase 2E and minimally disruptive to migrate for Phase 4.

## Decision

**Chosen approach: Synchronous sequential pipeline for Phase 2E, with an explicit async migration path documented here.**

Concretely:

- `SkillsInvoker.run(msg)` is a plain synchronous method. Each skill adapter (`_run_customer_identification`, `_run_sentiment_analysis`, etc.) calls its target function directly — no `await`, no event loop, no `asyncio.run()` wrapper.
- `apply_channel_adaptation(result, raw, channel, name)` is also synchronous.
- `SkillsRegistry` and `SkillManifest` are pure data structures — no async concern.
- `process_ticket` in `prototype.py` remains synchronous; calls `invoker.run()` and `invoker.apply_channel_adaptation()` inline.

**Phase 4 migration path (documented now to inform current design):**

```python
# Phase 2E — synchronous (current)
class SkillsInvoker:
    def run(self, msg: TicketMessage) -> InvokerResult:
        cid  = self._run_customer_identification(msg)
        sent = self._run_sentiment_analysis(msg, cid)
        kb   = self._run_knowledge_retrieval(msg)
        esc  = self._run_escalation_decision(msg, sent)
        return InvokerResult(cid, sent, kb, esc, channel_result=None)
```

```python
# Phase 4 — async (Kafka consumer context)
class AsyncSkillsInvoker(SkillsInvoker):
    async def run(self, msg: TicketMessage) -> InvokerResult:
        cid  = await self._run_customer_identification(msg)
        sent = await self._run_sentiment_analysis(msg, cid)
        kb   = await self._run_knowledge_retrieval(msg)
        esc  = await self._run_escalation_decision(msg, sent)
        return InvokerResult(cid, sent, kb, esc, channel_result=None)
```

The 5 adapter method bodies change only in two ways:
1. `def` → `async def`
2. Direct calls → `await` calls (where targets are also made async)

No structural refactoring is required — only `async/await` keyword additions.

**Migration contract for Phase 4:**
- Keep current `SkillsInvoker` (renamed `SyncSkillsInvoker`) — CLI and test reference.
- Create `AsyncSkillsInvoker(SyncSkillsInvoker)` overriding only `run` and `apply_channel_adaptation`.
- All tests against `SyncSkillsInvoker` continue to pass unchanged.
- Kafka worker (`src/workers/ticket_worker.py`) uses `AsyncSkillsInvoker` exclusively.
- **HIGH RISK**: `evaluate_escalation()` makes a blocking OpenAI API call — must be wrapped with `asyncio.to_thread()` in Phase 4 to avoid blocking the event loop.

## Consequences

### Positive

- **Zero friction for Phase 2E**: All existing tests run synchronously. No event loop needed. `pytest` runs without `pytest-asyncio`. 79+ tests stay green with no fixture changes.
- **Smallest possible diff**: Thin wrappers over existing synchronous functions. No threading overhead in the prototype.
- **Explicit migration path**: Phase 4 engineer knows exactly what changes (`async/await`) and what stays the same (method bodies, result types, invocation order).
- **No circular event loop risk**: Synchronous call stack keeps import graph flat — no event loop ownership ambiguity between `process_ticket`, the invoker, and the MCP server.
- **Compatible with CLI prototype**: Current CLI entry point (`prototype.py __main__`) is synchronous — no `asyncio.run()` wrapper needed.

### Negative

- **Cannot parallelize skill execution**: Skills 1–2 (Sentiment Analysis and Knowledge Retrieval) could theoretically run concurrently — they are independent. Sequential execution adds ~200–400ms. At 800 tickets/week (~7/hour), this is negligible for Phase 2E.
- **Phase 4 requires dual code-path maintenance**: `SyncSkillsInvoker` and `AsyncSkillsInvoker` coexist during the transition period. Mitigated by the subclass strategy — shared adapter logic stays in the base class.
- **Not thread-safe**: Assumes single-threaded execution. If Phase 3 FastAPI uses multi-threaded Uvicorn workers, the shared `ConversationStore` singleton becomes a race condition. Mitigation: Phase 3 must use async/single-threaded Uvicorn workers (the default and FastAPI best practice).
- **HIGH RISK — Blocking OpenAI call in async context**: `evaluate_escalation()` uses the synchronous OpenAI client. In Phase 4, this blocks the entire `asyncio` event loop for the duration of each API call (~500ms–2s). Must be wrapped with `asyncio.to_thread(evaluate_escalation, message)` in the `AsyncSkillsInvoker` override.

## Alternatives Considered

### Alternative A: Async-first now (use `asyncio.run()` in prototype)

Implement `SkillsInvoker.run()` as `async def` immediately; call from `process_ticket` via `asyncio.run()`.

- **Pro**: Phase 4 migration is trivial — remove the `asyncio.run()` wrapper.
- **Con**: `asyncio.run()` creates a new event loop per call. If called from within an existing event loop (e.g., some test fixtures), raises `RuntimeError: This event loop is already running`. Would require `pytest-asyncio` for all 79 existing tests or sync wrapper duplication.
- **Verdict**: Rejected. The 79-test stability constraint makes this unnecessarily risky.

### Alternative B: `concurrent.futures.ThreadPoolExecutor` for parallel skill execution

Run Sentiment Analysis and Knowledge Retrieval concurrently in a thread pool.

- **Pro**: ~200ms latency improvement per ticket; demonstrates parallelism.
- **Con**: `ConversationStore` singleton is not thread-safe. Thread pool adds non-determinism to test execution. At 800 tickets/week (~7/hour) the latency gain is invisible.
- **Verdict**: Rejected. Premature optimization with active thread-safety risk.

### Alternative C: `anyio` / `trio` compatibility layer

Use `anyio.from_thread.run_sync()` and `anyio.to_thread.run_sync()` to bridge sync and async.

- **Pro**: Maximum flexibility; compatible with both `asyncio` and `trio` backends.
- **Con**: `anyio` is not in the current requirements. Adds a new dependency and conceptual overhead. `aiokafka` requires `asyncio` specifically — `trio` compatibility is irrelevant.
- **Verdict**: Rejected. Out of scope for incubation phase.

## References

- Feature Spec: `specs/003-mcp-server/spec-2e-agent-skills.md`
- Implementation Plan: `specs/003-mcp-server/plan-2e-agent-skills.md`
- API Contract: `specs/003-mcp-server/contracts/skills_invoker_contract.py`
- Research Notes: `specs/003-mcp-server/research-2e.md`
- Related ADRs: ADR-0001 (ConversationStore Singleton — same async-unsafety noted in negative consequences; Phase 4 will replace singleton with FastAPI `Depends()`)
- Phase 4 migration trigger: Introduction of `aiokafka` consumer in `src/workers/ticket_worker.py`
- HIGH RISK: `evaluate_escalation()` blocking OpenAI call — must use `asyncio.to_thread()` in Phase 4 AsyncSkillsInvoker. Capture in Phase 4 plan as a mandatory pre-flight item.
