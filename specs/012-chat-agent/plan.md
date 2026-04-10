# Implementation Plan: Chat Agent Widget

**Branch**: `012-chat-agent` | **Date**: 2026-04-10 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `specs/012-chat-agent/spec.md`

---

## Summary

Build a floating AI chat widget (4th support channel: `web_chat`) for the NexaFlow portal. The widget consists of a FastAPI backend endpoint (`POST /chat/message`) that uses the OpenAI Agents SDK with two tools (`search_knowledge_base`, `get_session_history`), an in-memory session store with 20-message rate limiting, and a Next.js Client Component widget (floating button + animated panel + useChatSession hook). The chat channel is fully isolated from the Kafka/ticket pipeline — no ticket creation, no CRM writes. Non-streaming JSON response (ADR-0005).

**Multi-turn history pattern** (confirmed Context7): `result.to_input_list() + [{"role": "user", "content": msg}]` passed to `Runner.run()` on each turn. Server stores accumulated `input_items` per session, trimmed to last 20 items (10 turns).

---

## Technical Context

**Language/Version**: Python 3.12 (backend) + TypeScript 5 / Next.js 16.2.2 (frontend)  
**Primary Dependencies**:
- Backend: FastAPI, OpenAI Agents SDK (`agents`), Pydantic v2, asyncpg (pgvector KB search), langdetect (optional — see R-003)
- Frontend: React 19, Framer Motion (already installed), Tailwind CSS, shadcn/ui, next-themes
**Storage**: In-memory `dict[str, ChatSession]` (ephemeral) + existing Neon pgvector (read-only KB search)  
**Testing**: pytest + httpx `TestClient` (backend), no new frontend test tooling  
**Target Platform**: Hugging Face Spaces (FastAPI), Vercel (Next.js)  
**Performance Goals**: AI response P95 < 10 seconds (including RAG search + LLM call)  
**Constraints**: 20 msgs/session hard limit, 500 char input cap, non-streaming JSON, no DB writes  
**Scale/Scope**: Single-process HF Spaces deployment, in-memory state — not horizontally scalable in Phase 7B

---

## Constitution Check

| Rule | Check | Result |
|------|-------|--------|
| VI — OpenAI Agents SDK (not raw API) | Chat agent uses `Agent(...)` + `Runner.run()` — confirmed | ✅ PASS |
| IV.1 — PKT datetime injected | Chat agent `build_chat_system_prompt()` calls `datetime.now(ZoneInfo("Asia/Karachi"))` | ✅ PASS |
| IV.NEVER.1 — No competitors | System prompt includes competitor guardrail | ✅ PASS |
| IV.NEVER.8 — No system internals revealed | Prompt injection blocker at route level + prompt directive | ✅ PASS |
| III-1 — Kafka unified ingestion | **EXCEPTION**: Chat channel bypasses Kafka | ⚠️ JUSTIFIED |
| III-5 — Three-channel completeness | Chat is a 4th channel, not a replacement | ✅ PASS |

**Constitution Exception III-1 Justification**: The `web_chat` channel is a stateless self-service channel that does NOT create tickets. FR-022 explicitly scopes this. Kafka ingestion applies only to ticket-generating channels (Email, WhatsApp, Web Form). Chat responses are returned synchronously to the widget; no async queue required.

---

## Project Structure

### Documentation (this feature)

```text
specs/012-chat-agent/
├── plan.md               ← this file
├── spec.md               ← requirements (34 FRs, 5 stories)
├── research.md           ← Phase 0 research (R-001 to R-007)
├── data-model.md         ← ChatSession + API payload shapes
├── quickstart.md         ← local dev + smoke test checklist
├── contracts/
│   └── chat-endpoint.yaml ← OpenAPI 3.1 contract for POST /chat/message
└── checklists/
    └── requirements.md   ← spec quality checklist (all pass)
```

### Source Code Layout

```text
# Backend — new files in production/
production/
├── api/
│   ├── main.py                     ← MODIFY: register chat_router
│   └── chat_routes.py              ← NEW: POST /chat/message
└── chat/
    ├── __init__.py                 ← NEW
    ├── session_store.py            ← NEW: ChatSession dataclass + _sessions dict
    ├── chat_agent.py               ← NEW: Agent def + build_chat_system_prompt()
    ├── sanitizer.py                ← NEW: HTML strip + injection pattern blocklist
    └── schemas.py                  ← NEW: Pydantic v2 request/response models

# Frontend — new files in src/web-form/
src/web-form/
├── app/
│   └── layout.tsx                  ← MODIFY: add ChatWidgetPortal
├── components/
│   └── chat/
│       ├── ChatWidget.tsx          ← NEW: floating button + panel container
│       ├── ChatPanel.tsx           ← NEW: message list + header + input area
│       ├── ChatMessage.tsx         ← NEW: individual message bubble
│       └── ChatWidgetPortal.tsx    ← NEW: client wrapper (hides on /login)
└── hooks/
    └── useChatSession.ts           ← NEW: session state + API call logic

# Tests
tests/
├── test_chat_endpoint.py           ← NEW: rate limit, injection, session lifecycle
└── test_language_detection.py      ← NEW: Urdu → Urdu, English → English
```

---

## Phase 0: Research (Complete)

All research decisions confirmed. No blockers. See `research.md` for full rationale.

| Research Item | Decision |
|---------------|----------|
| R-001: Multi-turn history | Manual `input_items` — `result.to_input_list() + new_user_msg` per turn; store in ChatSession |
| R-002: Prompt injection | Blocklist of 9 patterns checked at route level before agent call |
| R-003: Language detection | System prompt instruction (no library); `langdetect` deferred to Phase 8 if needed |
| R-004: Session store | `dict[str, ChatSession]` with `dataclass`; same singleton pattern as ADR-0001 |
| R-005: Widget animation | Framer Motion (already installed); desktop = slide-up panel, mobile = fade-in full-screen |
| R-006: CORS | No changes — existing CORS config covers all origins |
| R-007: Layout insertion | Root `app/layout.tsx` + `ChatWidgetPortal` client component using `usePathname()` |

---

## Phase 1: Design & Contracts (Complete)

All Phase 1 artifacts written. See linked files.

- **Data model**: `data-model.md` — `ChatSession` backend entity, `ChatMessage` + `ChatSessionState` frontend interfaces, request/response payload shapes, error response table.
- **API contract**: `contracts/chat-endpoint.yaml` — OpenAPI 3.1, `POST /chat/message`, all request/response schemas, error codes (400/422/429/500), examples including Urdu.
- **Quickstart**: `quickstart.md` — local dev setup, new file list, manual smoke test checklist.

---

## Implementation Blocks

### Block 1 — Backend: FastAPI Chat Endpoint (HIGH PRIORITY)

**Files**: `production/chat/`, `production/api/chat_routes.py`, `production/api/main.py`

#### B1-T1: ChatSession store + schemas
- Create `production/chat/__init__.py` (empty)
- Create `production/chat/session_store.py`:
  - `ChatSession` dataclass: `session_id`, `input_items: list`, `message_count: int`, `created_at: datetime`
  - `_sessions: dict[str, ChatSession] = {}`
  - `get_or_create_session(session_id: str) -> ChatSession` — creates if empty/missing
  - `increment_and_get_result(session: ChatSession) -> SessionRateLimitResult`
  - `clear_session(session_id: str) -> None`
- Create `production/chat/schemas.py`:
  - `HistoryMessage(BaseModel)`: `role: Literal["user", "assistant"]`, `content: str`
  - `ChatMessageRequest(BaseModel)`: `message: str = Field(max_length=500)`, `session_id: str`, `history: list[HistoryMessage] = Field(max_length=20)`
  - `ChatMessageResponse(BaseModel)`: `reply: str`, `session_id: str`, `warning: str | None = None`

#### B1-T2: Input sanitizer
- Create `production/chat/sanitizer.py`:
  - `sanitize_message(raw: str) -> str` — strip HTML tags using regex (`<[^>]+>`), strip whitespace
  - `INJECTION_PATTERNS: list[str]` — 9 patterns from R-002
  - `check_injection(text: str) -> bool` — case-insensitive match against any pattern; returns `True` if injection detected

#### B1-T3: Chat agent definition
- Create `production/chat/chat_agent.py`:
  - `build_chat_system_prompt() -> str` — builds system prompt with injected PKT datetime:
    ```python
    current_dt = datetime.now(ZoneInfo("Asia/Karachi"))
    ```
    Prompt includes: NexaFlow support purpose, language detection instruction, competitor ban, off-topic refusal instruction (exact response text), system prompt concealment directive
  - `search_knowledge_base` tool — `@function_tool` that calls existing `production.agent.tools.search_knowledge_base` (reuses existing implementation). Input: `query: str`. Returns top-3 KB results as formatted string.
  - `get_session_history` tool — `@function_tool(name="get_session_history")`. Input: `session_id: str`. Reads from `_sessions[session_id].input_items`. Returns formatted conversation summary.
  - `build_chat_agent(session_id: str) -> Agent` — constructs `Agent(name="NexaFlow Chat Support", instructions=build_chat_system_prompt(), model="gpt-4o-mini", tools=[search_knowledge_base, get_session_history])`

#### B1-T4: Chat router
- Create `production/api/chat_routes.py`:
  - `router = APIRouter(prefix="/chat", tags=["chat"])`
  - `POST /chat/message` async handler:
    1. Sanitize `request.message` → reject if empty or > 500 chars after sanitization (HTTP 400)
    2. Check injection patterns → HTTP 422 if detected
    3. Retrieve/create session → check rate limit → HTTP 429 if `message_count >= 20`
    4. Increment `message_count`; compute `warning` string if count == 18 or 19
    5. Build `input_items`: convert `request.history` to input format + append new user message
    6. `Runner.run(agent, input_items)` — catch `openai.APIError` → HTTP 500 user-friendly message
    7. Extend session `input_items` with `result.to_input_list()[-2:]` (last assistant + user)
    8. Return `ChatMessageResponse(reply=result.final_output, session_id=session.session_id, warning=warning)`
- Modify `production/api/main.py`:
  - Add `from production.api.chat_routes import router as chat_router`
  - Add `app.include_router(chat_router)` after existing routers

**Acceptance**: `curl POST /chat/message {"message": "How to reset password?", "session_id": "", "history": []}` returns `{"reply": "...", "session_id": "uuid"}` with HTTP 200.

**HIGH RISK**: Session store uses module-level dict. HF Spaces may restart the process unpredictably, clearing all sessions. This is acceptable per spec (sessions are ephemeral) but means users lose chat history on server restart. Mitigation: clear warning in the error message.

---

### Block 2 — Frontend: Chat Widget Components (HIGH PRIORITY)

**Files**: `src/web-form/components/chat/`, `src/web-form/hooks/useChatSession.ts`

#### B2-T1: useChatSession hook
- Create `src/web-form/hooks/useChatSession.ts`:
  - State: `messages: ChatMessage[]`, `sessionId: string`, `isLoading: boolean`, `messageCount: number`, `warning: string | null`, `isLimitReached: boolean`
  - `sendMessage(text: string) → Promise<void>`:
    1. Append user message to `messages`
    2. Set `isLoading = true`
    3. Build `history` = last 10 items from `messages` (excluding the message just added)
    4. `POST /chat/message` with `{message: text, session_id: sessionId, history}`
    5. On success: append AI reply to `messages`, update `sessionId`, update `warning`, set `isLimitReached` if `messageCount >= 20`
    6. On error (network/500): append error message "I'm having trouble connecting…" to messages
    7. Set `isLoading = false`
  - `clearChat() → void`: Reset all state, set `sessionId = ""`
  - Initial greeting: first item in `messages` is always the greeting message

#### B2-T2: ChatMessage component
- Create `src/web-form/components/chat/ChatMessage.tsx` — `"use client"`
  - Props: `message: ChatMessage`
  - User messages: right-aligned, electric blue background (`bg-blue-500`), white text, rounded-bl-none
  - Assistant messages: left-aligned, dark surface (`bg-slate-800`), light text, rounded-bl-none
  - Timestamp shown below each message in small muted text

#### B2-T3: ChatPanel component
- Create `src/web-form/components/chat/ChatPanel.tsx` — `"use client"`
  - Props: `onClose: () => void`, `onMinimize: () => void`
  - Header: "NexaFlow AI Support" label, minimize button (ChevronDown icon), close button (X icon), clear-chat button (Trash2 icon) — all from `lucide-react`
  - Messages area: `useRef<HTMLDivElement>` for scroll container. `useEffect` watching `messages` → `ref.current.scrollTop = ref.current.scrollHeight` (auto-scroll)
  - Typing indicator: when `isLoading`, show three animated bouncing dots using Tailwind `animate-bounce` with staggered delays
  - Input area: `<textarea>` (single-line, Enter to send, Shift+Enter for newline), send button — disabled when `isLoading || isLimitReached || input.trim() === ""`
  - Rate limit warning: show `warning` text in amber below messages area when present
  - Limit reached: show "Session limit reached. Please submit a support ticket." with link to `/support`
  - Footer: "Powered by NexaFlow AI" in muted small text
  - Character counter: show `{input.length}/500` below textarea when input.length > 400

#### B2-T4: ChatWidget (container + floating button)
- Create `src/web-form/components/chat/ChatWidget.tsx` — `"use client"`
  - State: `isOpen: boolean`, `isMinimized: boolean`, `isMobile: boolean`
  - `isMobile`: `useEffect(() => { setIsMobile(window.innerWidth < 768) }, [])`
  - Floating button: `fixed bottom-6 right-6 z-50` — electric blue circle (`bg-blue-500`), MessageCircle icon (lucide-react), 56px diameter. `onClick → setIsOpen(true)`
  - `AnimatePresence` from `framer-motion` wrapping the panel:
    - Desktop panel: `motion.div fixed bottom-24 right-6 z-50 w-[380px] h-[520px] bg-[#0F172A] rounded-2xl shadow-2xl border border-slate-700`
      - `initial={{ y: 20, opacity: 0 }}` → `animate={{ y: 0, opacity: 1 }}` → `exit={{ y: 20, opacity: 0 }}`
    - Mobile panel: `motion.div fixed inset-0 z-50 bg-[#0F172A]`
      - `initial={{ opacity: 0 }}` → `animate={{ opacity: 1 }}` → `exit={{ opacity: 0 }}`
  - Minimized state (desktop only): panel collapses to header-height-only div (hide messages + input)
  - Passes `onClose` and `onMinimize` callbacks to ChatPanel

---

### Block 3 — Integration: Layout & Login Exclusion (MEDIUM PRIORITY)

**Files**: `src/web-form/app/layout.tsx`, `src/web-form/components/chat/ChatWidgetPortal.tsx`

#### B3-T1: ChatWidgetPortal (client wrapper)
- Create `src/web-form/components/chat/ChatWidgetPortal.tsx` — `"use client"`
  - `const pathname = usePathname()` from `next/navigation`
  - `if (pathname === '/login') return null`
  - `return <ChatWidget />`
  - This is a thin wrapper; the actual widget logic lives in `ChatWidget.tsx`

#### B3-T2: Root layout modification
- Modify `src/web-form/app/layout.tsx`:
  - Import: `import ChatWidgetPortal from "@/components/chat/ChatWidgetPortal"`
  - Add `<ChatWidgetPortal />` inside `<ThemeProvider>`, after `{children}` and before `<Toaster />`
  - Root layout remains a Server Component — `ChatWidgetPortal` is the Client Component boundary

**Acceptance**: Widget appears on `/dashboard`, `/support`, `/ticket/[id]`. Widget does NOT appear on `/login`.

---

### Block 4 — Tests (MEDIUM PRIORITY)

**Files**: `tests/test_chat_endpoint.py`, `tests/test_language_detection.py`

#### B4-T1: Chat endpoint unit tests
- Create `tests/test_chat_endpoint.py`:
  - Use `httpx.AsyncClient` with FastAPI `TestClient`; mock `Runner.run()` with `unittest.mock.AsyncMock`
  - `test_first_message_creates_session` — empty `session_id` → response has UUID `session_id`
  - `test_rate_limit_warning_at_18` — simulate 18 messages → response includes `warning` field
  - `test_rate_limit_hard_block_at_20` — simulate 20 messages → HTTP 429
  - `test_prompt_injection_rejected` — message with "ignore previous instructions" → HTTP 422
  - `test_html_stripped_from_message` — message with `<script>alert(1)</script>` → sanitized and processed
  - `test_empty_message_rejected` — empty string → HTTP 400
  - `test_message_too_long_rejected` — 501-char message → HTTP 400
  - `test_clear_chat_new_session` — send with `session_id=""` after existing session → new UUID returned

#### B4-T2: Language detection tests
- Create `tests/test_language_detection.py`:
  - These are integration tests that call the actual agent (skipped in CI without API key)
  - `test_urdu_input_urdu_response` — send Urdu message → verify response contains Urdu characters (non-ASCII)
  - `test_english_input_english_response` — send English message → verify response is ASCII/English
  - Mark with `@pytest.mark.integration` for CI skip control

---

## Complexity Tracking

| Area | Added Complexity | Justified Because |
|------|-----------------|-------------------|
| Module-level `_sessions` dict | Non-thread-safe in theory | Single-process HF Spaces deployment; asyncio event loop serializes requests; same pattern as ADR-0001 |
| Framer Motion `AnimatePresence` | Additional client-side JS bundle | Already installed; no alternative for smooth enter/exit animation in Next.js Client Components |
| Two separate layout files | Both root and (main) layout exist | ChatWidget goes in root layout for universal coverage; existing (main) layout unchanged |

---

## Risk Register

| Risk | Severity | Mitigation |
|------|----------|------------|
| **HIGH**: HF Spaces server restart clears `_sessions` → active users lose chat mid-session | Medium | Ephemeral by design (spec assumption 3); widget shows error message gracefully on reconnect |
| **HIGH**: gpt-4o-mini occasionally ignores off-topic refusal instruction | Medium | Test B4-T1 validates refusal via system prompt; blocklist at route level catches most cases |
| **MEDIUM**: `to_input_list()` format incompatibility if Agents SDK updates | Low | Pin SDK version in requirements.txt; confirmed against v0.7.0 docs |
| **MEDIUM**: Mobile viewport detection race condition (SSR mismatch) | Low | `useEffect` sets `isMobile` client-side only; no SSR hydration mismatch if initial render defaults to desktop layout |
| **LOW**: Framer Motion bundle size | Negligible | Already installed; no new dependency added |

---

## Task Count Summary

| Block | Tasks | Priority |
|-------|-------|----------|
| Block 1 — Backend Endpoint | 4 tasks (B1-T1 to B1-T4) | HIGH |
| Block 2 — Frontend Widget | 4 tasks (B2-T1 to B2-T4) | HIGH |
| Block 3 — Layout Integration | 2 tasks (B3-T1, B3-T2) | MEDIUM |
| Block 4 — Tests | 2 tasks (B4-T1, B4-T2) | MEDIUM |
| **Total** | **12 tasks** | |

---

## HIGH RISK Tasks

1. **B1-T4 (Chat router)** — Integration point between sanitizer, session store, and Agents SDK. Any mismatch in `input_items` format or `Runner.run()` behavior causes silent failures. Must test with actual agent calls (not just mocks) before declaring done.
2. **B1-T3 (Chat agent)** — System prompt must be precisely worded to enforce off-topic refusal and multilingual detection. Guardrail effectiveness depends entirely on prompt quality.
3. **B2-T1 (useChatSession hook)** — Central state machine for the widget. Session ID lifecycle (empty → UUID → clear → empty) must handle all edge cases correctly, especially concurrent rapid clicks.

---

## Definition of Done

- [ ] `POST /chat/message` returns AI reply in < 10 seconds for a NexaFlow product question
- [ ] Off-topic refusal returns exact string: "I'm here to help with NexaFlow support only. What can I help you with?"
- [ ] Rate limit: warning at message 18, input disabled at message 20
- [ ] Widget appears on all pages except `/login`
- [ ] Mobile (<768px) opens full-screen overlay; desktop opens 380×520 panel
- [ ] Messages area auto-scrolls to latest message on every new message
- [ ] All 8 unit tests in `test_chat_endpoint.py` pass
- [ ] Clear chat resets session, greeting reappears
- [ ] Prompt injection message (e.g., "ignore previous instructions") → HTTP 422 from endpoint
