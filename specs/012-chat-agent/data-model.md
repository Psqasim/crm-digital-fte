# Data Model: Phase 7B — Chat Agent Widget
**Branch**: `012-chat-agent` | **Date**: 2026-04-10 | **Phase**: Phase 1 Output

> The chat channel is fully ephemeral. No new database tables are created. All state lives in-memory on the backend and in React component state on the frontend. Session data is lost on server restart (expected — sessions are stateless by design per FR-022).

---

## Backend In-Memory Entities

### ChatSession

Represents one user's conversation in the chat widget. Lives in a module-level dict keyed by `session_id`.

```python
@dataclass
class ChatSession:
    session_id: str          # UUID v4, generated on first message
    input_items: list        # OpenAI Agents SDK accumulated input list (to_input_list())
                             # Trimmed to last 20 items (10 user + 10 assistant turns)
    message_count: int       # Number of user messages sent (rate limit counter)
    created_at: datetime     # UTC creation timestamp (for future TTL cleanup)
```

**State transitions**:
```
[Not Exists]
    │ (first message received, session_id="" or missing)
    ▼
[Active: message_count=1]
    │ (each subsequent message)
    ▼
[Active: message_count=2..17]
    │ (message 18 sent — soft warning triggered)
    ▼
[Warning: message_count=18..19]
    │ (message 20 sent — hard limit enforced)
    ▼
[Locked: message_count=20] ── HTTP 429 returned for all subsequent requests
    │
    OR
    │ (clear-chat triggered by frontend — new session_id issued)
    ▼
[New Session — fresh ChatSession with message_count=0]
```

**Store interface**:
```python
_sessions: dict[str, ChatSession] = {}

def get_or_create_session(session_id: str) -> ChatSession
def increment_and_check(session: ChatSession) -> tuple[bool, str]  
    # Returns (is_allowed, warning_message | "")
def clear_session(session_id: str) -> None
    # Called when frontend sends empty session_id (clear-chat)
```

---

### SessionRateLimitResult

Returned by the rate limit check. Not persisted — computed per request.

```python
@dataclass
class SessionRateLimitResult:
    allowed: bool           # False when message_count >= 20
    warning: str | None     # Set when message_count == 18 → "You have 2 messages remaining"
                            # Set when message_count == 19 → "You have 1 message remaining"
    count: int              # Current message_count after increment
```

---

## Frontend In-Memory Entities (React State)

### ChatMessage (display model — TypeScript)

Represents one message bubble in the chat panel. Lives in `useState<ChatMessage[]>`.

```typescript
interface ChatMessage {
  id: string           // crypto.randomUUID() — for React key
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}
```

### ChatSessionState (hook state — TypeScript)

Managed by `useChatSession` hook.

```typescript
interface ChatSessionState {
  sessionId: string         // "" on init, UUID after first message
  messages: ChatMessage[]   // All messages for display
  isLoading: boolean        // True while awaiting AI response
  messageCount: number      // Mirrors backend count (from response metadata)
  warning: string | null    // Rate limit warning message if any
  isLimitReached: boolean   // True when messageCount >= 20
}
```

---

## API Payload Shapes

### POST /chat/message — Request Body

```typescript
interface ChatMessageRequest {
  message: string      // 1–500 chars, sanitized
  session_id: string   // "" on first message, UUID on subsequent
  history: Array<{     // Last 10 messages for context (display history)
    role: 'user' | 'assistant'
    content: string
  }>
}
```

### POST /chat/message — Response Body

```typescript
interface ChatMessageResponse {
  reply: string         // AI-generated response text
  session_id: string    // UUID (same as request, or new if first message)
  warning?: string      // Rate limit warning (present when message_count is 18 or 19)
}
```

### POST /chat/message — Error Responses

| HTTP Status | When | Body |
|-------------|------|------|
| 400 | Message empty, too long (>500 chars), or HTML injection detected | `{"detail": "Message too long (max 500 characters)"}` |
| 422 | Prompt injection pattern detected | `{"detail": "I can't process that request. Please keep questions about NexaFlow support."}` |
| 429 | Session has reached 20-message limit | `{"detail": "Session limit reached. Please submit a formal support ticket."}` |
| 500 | AI backend error (OpenAI API failure) | `{"detail": "I'm having trouble connecting. Please try again or use our support form."}` |

---

## Existing Data Entities (Read-Only — Not Modified)

The chat endpoint reads from these existing database tables but never writes:

### knowledge_base (existing, pgvector)

```sql
-- Already seeded with 11 chunks (Phase 6)
CREATE TABLE knowledge_base (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    embedding vector(1536),
    metadata JSONB
);
```

The `search_knowledge_base` tool used by the chat agent performs a cosine similarity search against this table. No new rows are written by the chat channel.
