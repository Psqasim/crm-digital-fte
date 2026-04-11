# Project Evolution: Incubation → Production

How CRM Digital FTE Factory evolved from a prototype script to a production-grade system.

---

## Stage 1: Incubation (Phases 2A–2F)

Building the prototype, discovering requirements, crystallizing the spec.

| Phase | What Was Built | Key Discovery |
|-------|---------------|---------------|
| 2A | Ticket analysis script | 14 requirements found; LLM-intent classification beats keyword matching |
| 2B | Prototype core loop | 6-step pipeline: normalize → search → escalate → generate → format |
| 2C | Memory & state | `ConversationStore`, cross-channel identity (phone → email dedup) |
| 2D | MCP server | 7 tools via FastMCP stdio transport |
| 2E | Agent skills | 5 skills, `SkillsInvoker` pipeline (priority 0→4) |
| 2F | Crystallized spec | 1,064-line spec, 101 tests passing |

---

## Stage 2: Specialization (Phases 4A–4G)

Replacing every prototype component with a production-grade equivalent.

| Phase | What Was Built | Production Upgrade from Prototype |
|-------|---------------|----------------------------------|
| 4A | PostgreSQL schema | In-memory dict → Neon + pgvector (8 tables) |
| 4B | OpenAI Agents SDK | Prototype functions → `@function_tool` + Pydantic models |
| 4C | Channel handlers + Web Form | Stub handlers → Gmail API + Twilio + Next.js 4-page form |
| 4D | FastAPI orchestration | Single script → 8 REST endpoints + `BackgroundTasks` |
| 4E | Kafka streaming | Print statements → Confluent Cloud real-time pipeline |
| 4F | Docker + Kubernetes | Local-only → containerized + K8s manifests (Minikube/Oracle Cloud) |
| 4G | Monitoring | No observability → `/metrics/channels`, `/metrics/summary`, structured JSON logs |

---

## Stage 3: Integration (Phase 5)

End-to-end wiring, documentation, and knowledge base.

| Task | What Was Done |
|------|--------------|
| Knowledge base seeded | 11 chunks from `context/product-docs.md` via `text-embedding-3-small` → pgvector |
| E2E test suite | 5 tests covering web form flow, cross-channel identity, escalation path, metrics, health |
| Docs | `docs/` subfolder structure: setup, env, api, deploy, web-form |
| MIT License | Added |

---

## Test Coverage Growth

| After Phase | Tests Passing |
|-------------|--------------|
| 2B | 16 |
| 2C | 52 |
| 2D | 79 |
| 2E | 101 |
| 4B | 122 |
| 4C | 142 |
| 4D | 150 |
| 4E | 162 |
| 5  | 166 |

---

## Architecture Decisions

| ADR | Decision | Rationale |
|-----|----------|-----------|
| ADR-0001 | `ConversationStore` as injectable dependency | Enables testing without a real DB; production swaps to asyncpg pool |
| ADR-0002 | Sync skill pipeline → async for Kafka | `aiokafka` requires `async/await` throughout; forced upgrade from Phase 2 sync pattern |
| ADR-0003 | Pydantic `BaseModel` for all `@function_tool` inputs | OpenAI Agents SDK requires typed schemas; Pydantic v2 generates them automatically |
| ADR-0004 | pgvector over Pinecone | Keeps vector search co-located with relational data in Neon; avoids a separate vector DB service |
| ADR-0005 | Confluent Cloud over self-hosted Kafka | Managed Kafka with no infra overhead; free tier sufficient for hackathon scale |

---

## Stage 4: Enhancement (Phases 7A–7B)

Securing internal access and adding a 4th AI support channel.

| Phase | What Was Built | Why |
|-------|---------------|-----|
| 7A | NextAuth.js v5 RBAC — login page, admin dashboard, agent account creation, role-based routes | Secure internal access; differentiate admin vs agent vs public views |
| 7B | AI Chat Widget — floating button, RAG, multilingual, guardrails, session management, mobile-first | 4th support channel for quick Q&A; portfolio impact; real AI interaction on the live site |

### Key decisions in Stage 4

- **JWT strategy (not DB sessions)** — stateless, compatible with HF Spaces ephemeral containers
- **`proxy.ts` not `middleware.ts`** — Next.js 16.2.2 renamed the middleware entrypoint (ADR-0004)
- **Non-streaming chat** — `Runner.run()` over `Runner.run_streamed()` — simpler, more reliable on HF Spaces single-process runtime (ADR-0005)
- **Chat isolated from ticket pipeline** — no Kafka, no DB writes for chat; in-memory sessions only
- **State lifted to ChatWidget** — session state owned at widget level so minimize/close cycles don't wipe conversation history

### Test growth

| Stage | Tests Passing |
|-------|--------------|
| After Stage 1 (incubation) | 101 |
| After Stage 2 (specialization) | 166 |
| After Stage 3 (integration/Phase 5) | 166 |
| After Stage 4 (enhancement/Phase 7B) | 176 |
