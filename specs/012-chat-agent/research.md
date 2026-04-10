# Research: Phase 7B — Chat Agent Widget
**Branch**: `012-chat-agent` | **Date**: 2026-04-10 | **Phase**: Phase 0 Output

---

## R-001: OpenAI Agents SDK — Multi-Turn Conversation History

**Question**: How does the OpenAI Agents SDK handle conversation history across multiple turns for the chat endpoint?

**Decision**: Use the **manual `input_items` pattern** — server stores accumulated `input_items` per session, appends new user message on each turn, passes full list to `Runner.run()`.

**Confirmed via Context7** (`/openai/openai-agents-python`):

```python
# First turn
result = await Runner.run(agent, "User message 1")
# result.to_input_list() = [user_msg_1, assistant_msg_1]

# Second turn — append new user message to prior output
new_input = result.to_input_list() + [{"role": "user", "content": "User message 2"}]
result = await Runner.run(agent, new_input)
```

**Implementation for chat endpoint**:
- `ChatSession.input_items: list` — accumulated `to_input_list()` output per session
- On each request: retrieve session `input_items`, append `{"role": "user", "content": sanitized_message}`, call `Runner.run(agent, input_items)`, extend store with `result.to_input_list()[-n:]`
- Token budget: Keep last 10 turns (20 items = 10 user + 10 assistant) to stay within gpt-4o-mini context limits

**Alternatives considered**:
- `SQLiteSession`: Automatic persistence to SQLite DB. Rejected — sessions are ephemeral (in-memory only), no DB persistence required. Adds a file dependency on HF Spaces for no benefit.
- `session=InMemorySession()`: OpenAI SDK also offers in-memory session objects. Could work, but manual `input_items` gives us explicit control over the 10-turn window without needing to implement a custom session trimmer.

**Rationale for chosen approach**: Manual `input_items` gives explicit control over context window trimming, integrates cleanly with the in-memory `ChatSession` store, and requires zero external dependencies.

---

## R-002: Input Sanitization & Prompt Injection Detection

**Question**: What patterns constitute a prompt injection attempt? What sanitization is needed?

**Decision**: Two-layer defense:
1. **HTML strip**: Remove all HTML tags before processing (regex or `bleach` library).
2. **Injection pattern blocklist**: Reject messages containing any of these case-insensitive patterns:
   - `ignore previous instructions`
   - `ignore your instructions`
   - `you are now`
   - `forget your instructions`
   - `forget everything`
   - `new persona`
   - `act as`
   - `disregard your`
   - `override your`
   - `system prompt`

**Rationale**: These patterns are the most common jailbreak/injection attempts targeting instruction-following LLMs. The check must happen BEFORE the message reaches the agent (rejected at the FastAPI route level, not inside the agent).

**Alternatives considered**: LLM-based injection detection (use another model to classify intent). Rejected — adds latency and cost; blocklist is fast, free, and sufficient for known patterns.

---

## R-003: Language Detection Approach

**Question**: How should the chat agent auto-detect the user's language and respond in the same language?

**Decision**: **System prompt instruction** — instruct the agent to detect the user's language from the message content and respond in the same language. No external library needed for Phase 7B.

**System prompt directive**:
```
Detect the language of the user's message. If the user writes in Urdu, respond in Urdu.
If the user writes in English, respond in English. If the language is mixed or unclear,
default to English. NEVER switch languages mid-conversation.
```

**Alternatives considered**:
- `langdetect` library: Python library for language classification. More accurate for short text. Could be used as a pre-processing step to inject `Language: Urdu` into the system prompt per request. Simpler to implement correctly but adds a dependency.
- `langdetect` as pre-step: Feasible for Phase 8 enhancement if system prompt instruction proves insufficient for very short Urdu messages.

**Rationale**: System prompt instruction is sufficient for gpt-4o-mini which has strong multilingual capability. Zero additional dependencies. If accuracy proves insufficient in testing, switch to langdetect pre-step.

---

## R-004: In-Memory Session Store Design

**Question**: What is the right structure for the ChatSession in-memory store?

**Decision**:
```python
@dataclass
class ChatSession:
    session_id: str
    input_items: list          # accumulated Runner input_items (trimmed to 20 items = 10 turns)
    message_count: int         # user messages sent (for rate limiting)
    created_at: datetime       # for optional future TTL cleanup

# Module-level store (same pattern as ADR-0001 singleton)
_sessions: dict[str, ChatSession] = {}
```

**Rate limit enforcement**: `message_count` incremented on every validated user message. Checked before calling the agent. Returns HTTP 429 when `message_count >= 20`.

**TTL / cleanup**: Not implemented in Phase 7B. Sessions accumulate until server restart (HF Spaces restarts clear them). For Phase 8, add a background task to evict sessions older than 24 hours.

**Alternatives considered**: Redis for distributed rate limiting. Rejected — single-process HF Spaces deployment, no distributed rate limiting needed.

---

## R-005: Frontend Widget — Framer Motion + Mobile Breakpoint

**Question**: How should the widget animate and behave on mobile?

**Decision**:
- **Desktop (≥768px)**: Floating button (fixed, bottom-right, z-50). On click → panel animates up with Framer Motion `AnimatePresence` + `motion.div` with `initial: {y: 20, opacity: 0}` → `animate: {y: 0, opacity: 1}`.
- **Mobile (<768px)**: Same floating button. On click → full-screen overlay using `motion.div` with `fixed inset-0` class. Framer Motion `initial: {opacity: 0}` → `animate: {opacity: 1}` (fade in).

**Breakpoint detection**: CSS media query via Tailwind (`sm:` prefix or `useMediaQuery` hook). Use `window.innerWidth < 768` in a `useEffect` to set `isMobile` state, OR use pure Tailwind conditional classes where possible.

**Framer Motion already installed**: Confirmed in `src/web-form/package.json` via `components/animations/FadeIn.tsx` and `SlideUp.tsx` — Framer Motion is in the dependency tree.

---

## R-006: CORS Configuration for New Chat Endpoint

**Question**: Does the new `/chat/message` endpoint need CORS changes?

**Decision**: No changes needed. `production/api/main.py` already configures CORS with `allow_origins` covering `localhost:3000` and `*.vercel.app`. The new chat router is registered on the same FastAPI app, inheriting the existing CORS middleware.

---

## R-007: Where to Register ChatWidget in Next.js Layout

**Question**: The spec says "appears on all pages, NOT on /login". How to implement in Next.js 16 App Router?

**Decision**: Add `ChatWidget` to root `app/layout.tsx` as a `"use client"` component wrapper (`ChatWidgetPortal`) that uses `usePathname()` to skip rendering on `/login`.

**Why root layout**: Root `app/layout.tsx` wraps all pages including the `(main)` route group. Adding to `(main)/layout.tsx` would exclude pages outside the group (none currently, but future-proof). Root layout is the correct insertion point.

**Pattern**:
```tsx
// components/chat/ChatWidgetPortal.tsx — "use client"
const pathname = usePathname()
if (pathname === '/login') return null
return <ChatWidget />
```

Root `layout.tsx` remains a Server Component — it imports `ChatWidgetPortal` (a Client Component boundary). This is the standard Next.js pattern for conditional client-side rendering in layouts.
