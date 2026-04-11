# Quickstart: Phase 7B — Chat Agent Widget
**Branch**: `012-chat-agent` | **Date**: 2026-04-10

---

## What's Being Added

A floating AI chat widget for NexaFlow — bottom-right corner of every page. Powered by the existing OpenAI Agents SDK agent. Fourth support channel (`web_chat`), fully isolated from the ticket pipeline.

---

## Backend — New Files

```
production/
└── api/
    └── chat_routes.py          # NEW — POST /chat/message router
production/
└── chat/                       # NEW module
    ├── __init__.py
    ├── session_store.py        # ChatSession dataclass + _sessions dict
    ├── chat_agent.py           # Agent definition (2 tools: search_kb + get_session_history)
    ├── sanitizer.py            # HTML strip + injection pattern detection
    └── schemas.py              # ChatMessageRequest, ChatMessageResponse (Pydantic v2)
tests/
├── test_chat_endpoint.py       # NEW — endpoint tests (mocked agent)
└── test_language_detection.py  # NEW — Urdu input → Urdu response
```

**Register router in `production/api/main.py`**:
```python
from production.api.chat_routes import router as chat_router
app.include_router(chat_router)   # /chat/message
```

---

## Frontend — New Files

```
src/web-form/
└── components/
    └── chat/
        ├── ChatWidget.tsx        # NEW — floating button + panel container
        ├── ChatPanel.tsx         # NEW — message list + header + input
        ├── ChatMessage.tsx       # NEW — individual message bubble
        └── ChatWidgetPortal.tsx  # NEW — client wrapper for layout (hides on /login)
└── hooks/
    └── useChatSession.ts         # NEW — session state + API call logic
```

**Modify `src/web-form/app/layout.tsx`**:
```tsx
// Add before closing </body>:
import ChatWidgetPortal from "@/components/chat/ChatWidgetPortal"
// Inside RootLayout:
<ChatWidgetPortal />
```

---

## Backend: Local Development

```bash
# From repo root
cd /home/ps_qasim/projects/crm-digital-fte
source .venv/bin/activate  # or: uv run

# Run FastAPI with new chat router
uvicorn production.api.main:app --reload

# Test the chat endpoint
curl -X POST http://localhost:8000/chat/message \
  -H "Content-Type: application/json" \
  -d '{"message": "How do I connect to Slack?", "session_id": "", "history": []}'

# Expected response:
# {"reply": "Hi! To connect NexaFlow to Slack...", "session_id": "uuid-here"}
```

---

## Frontend: Local Development

```bash
cd src/web-form
npm run dev
# Open http://localhost:3000
# Floating chat button should appear bottom-right on all pages except /login
```

---

## Environment Variables

No new env vars required for this phase. The chat endpoint uses:
- `OPENAI_API_KEY` — already set (used by existing agent)
- `DATABASE_URL` — already set (used by `search_knowledge_base` tool)

---

## Key Architectural Constraints

1. **Non-streaming JSON only** (ADR-0005) — `POST /chat/message` returns full reply as JSON. No SSE.
2. **Manual input_items** (R-001) — backend accumulates `result.to_input_list()` per session; trims to last 10 turns.
3. **No ticket creation** (FR-022) — chat endpoint NEVER calls `create_ticket` or publishes to Kafka.
4. **In-memory only** — `_sessions` dict cleared on server restart. No DB writes.
5. **PKT datetime injected** — chat agent system prompt gets `datetime.now(ZoneInfo("Asia/Karachi"))` per call (constitution §IV.1).

---

## Testing Checklist (Manual Smoke Test)

- [ ] Open chat widget → greeting appears
- [ ] Ask "How do I connect to Slack?" → AI responds with relevant answer
- [ ] Ask "Write me an essay" → exact refusal: "I'm here to help with NexaFlow support only."
- [ ] Ask in Urdu → response in Urdu
- [ ] Send 18 messages → warning appears
- [ ] Send 20 messages → input disabled, support form link shown
- [ ] Click clear chat → fresh greeting, new session
- [ ] On mobile viewport (<768px) → widget opens full-screen
- [ ] Navigate to /login → widget NOT visible
- [ ] Navigate to /dashboard → widget visible
