# ADR-0005: Chat Endpoint — Streaming vs Non-Streaming Response Design

- **Status:** Accepted
- **Date:** 2026-04-10
- **Feature:** 012-chat-agent (Phase 7B — Chat Agent Widget)
- **Context:** Phase 7B introduces a new `POST /chat/message` endpoint on the FastAPI backend (deployed on Hugging Face Spaces). The endpoint receives a user message, a session ID, and up to 10 messages of conversation history. It performs a knowledge base vector search, then calls the OpenAI Agents SDK to generate an AI support response, and delivers that response to the Next.js chat widget frontend. The widget already displays a typing indicator while waiting. Two response delivery patterns were evaluated before implementation began — the choice affects endpoint architecture, frontend fetch strategy, error handling, and HF Spaces deployment behaviour.

<!-- Significance checklist
     1) Impact: Yes — switching later requires changes to both backend (endpoint type) and frontend (event consumer pattern); affects HF Spaces connection handling.
     2) Alternatives: Yes — two viable, fully-documented options with different tradeoffs.
     3) Scope: Yes — cross-cutting: FastAPI route design, Next.js fetch pattern, widget state management, and deployment platform constraints.
     All three true → ADR justified. -->

## Decision

**Chosen approach: Non-streaming JSON response (`Runner.run()` + standard `POST` → `{reply: str, session_id: str}`).**

Concretely:
- **Backend endpoint**: `POST /chat/message` uses `await Runner.run(agent, message)` and returns `{"reply": str, "session_id": str}` as standard JSON. No SSE, no `ReadableStream`, no chunked transfer encoding.
- **Knowledge base search**: RAG step runs before the `Runner.run()` call; results are injected into the agent context. Total backend latency: ~1.5–5 seconds (RAG ~200–500ms + LLM ~1–4s for 50–200 token responses from gpt-4o-mini).
- **Frontend**: Standard `fetch` POST, `await response.json()`, then set message state. Typing indicator (three animated dots) is shown during the await — it adequately communicates "AI is thinking" for this response time range.
- **Error handling**: Standard HTTP status codes (422 for validation errors, 429 for rate limit, 500 for upstream AI failures). No mid-stream failure recovery logic required.
- **Upgrade path**: If streaming is desired in Phase 8, the backend adds a `GET /chat/stream/{session_id}` SSE route; the frontend replaces the `fetch` call with an `EventSource` consumer. The non-streaming endpoint remains as a fallback. The two approaches do not conflict.

## Consequences

### Positive

- **Implementation simplicity**: Standard async POST/JSON is one pattern both backend and frontend developers know well. No event-stream parsing, no partial-message state, no re-connection logic.
- **Testability**: The endpoint can be fully tested with standard HTTP clients (curl, pytest's `TestClient`, Postman). No SSE consumer or stream simulation required in tests.
- **HF Spaces reliability**: Hugging Face Spaces supports standard HTTP POST/JSON responses without configuration. Long-lived SSE connections require explicit timeout tuning on HF Spaces infrastructure, which is not documented for the free tier.
- **Predictable error handling**: A single HTTP response means a single failure mode — no partial-delivery edge cases to handle (stream interrupted mid-token, client disconnects before close frame).
- **Typing indicator is sufficient**: For gpt-4o-mini responses of 50–200 tokens (~1–4 seconds), the typing indicator provides the "something is happening" signal users need. Streaming's UX advantage is pronounced for 30-second responses (code generation, essays), not 3-second support answers.

### Negative

- **Perceived latency**: The full response appears at once rather than building up progressively. Users may perceive a 3–5 second wait as "slow" even if total time is identical to a streaming implementation.
- **No progressive disclosure**: A long AI response (e.g., a multi-step integration guide) cannot be read while still being generated. User must wait for the complete answer.
- **Future refactor cost**: Adding streaming later requires frontend changes (EventSource/ReadableStream consumer, streaming state management) and a new backend SSE route. Not zero-cost, but low compared to the up-front complexity if streaming were chosen now.

## Alternatives Considered

### Alternative A — Streaming via Server-Sent Events (`Runner.run_streamed()` + SSE)

- **How it works**: Backend calls `Runner.run_streamed(agent, message)`, iterates `async for event in result.stream_events()`, extracts `ResponseTextDeltaEvent` deltas, and sends each delta as an SSE event. Frontend uses `EventSource` or `fetch` with `ReadableStream` to consume tokens as they arrive, appending each delta to the displayed message.
- **Pros**: Progressive text display ("typing" effect) — modern chat product UX; users can start reading before the full response is ready.
- **Cons**:
  - HF Spaces SSE reliability is not documented for long-lived connections on the free tier; timeouts may interrupt streams silently.
  - Frontend requires partial-message state management (building string from deltas), stream error handling, and optional reconnection logic — ~3× more frontend code than non-streaming.
  - Backend requires SSE response headers, generator-based route handler, and stream cleanup on client disconnect — harder to test with standard HTTP tools.
  - For 50–200 token responses at gpt-4o-mini speed, the streaming effect plays out in ~1–3 seconds — marginal UX improvement over a typing indicator + instant delivery.
- **Why rejected**: Complexity cost outweighs UX benefit at this response length and token speed. HF Spaces infrastructure risk makes it an unsafe default for a hackathon demo. Streaming is preserved as an explicit Phase 8 enhancement.

### Alternative B — WebSocket Persistent Connection

- **How it works**: Frontend opens a WebSocket to the backend on widget load. Messages and responses travel over the persistent socket. Backend can push tokens as they arrive or send the full response.
- **Pros**: Bidirectional, low-latency, enables real-time features (typing indicators from server, push notifications).
- **Cons**: WebSocket support on HF Spaces requires additional configuration and is not guaranteed. Adds connection lifecycle management (open, close, reconnect) to both frontend and backend. Significantly higher complexity than either HTTP option. No meaningful UX advantage over SSE for unidirectional AI replies.
- **Why rejected**: Disproportionate complexity for a one-way AI reply stream. Not supported out-of-the-box on HF Spaces free tier.

## References

- Feature Spec: `specs/012-chat-agent/spec.md` (FR-029 – FR-034: Chat API Endpoint requirements)
- Context7 Research: OpenAI Agents SDK `Runner.run_streamed()` — `history/prompts/012-chat-agent/0001-phase-7b-chat-agent-widget-spec.spec.prompt.md`
- Related ADRs: ADR-0002 (Skill Pipeline synchronous design), ADR-0003 (Tool input schema)
- Evaluator Evidence: PHR-0001 (012-chat-agent) — Context7 streaming research results confirmed
