# Implementation Plan: Phase 4C — Gmail & WhatsApp Channel Handlers

**Branch**: `006-production-agent` | **Date**: 2026-04-04
**Spec**: `specs/006-production-agent/spec-4c-channel-handlers.md`

---

## Summary

Phase 4C replaces three `# Phase 4X will implement this` stubs with working code:
`production/channels/gmail_handler.py`, `production/channels/whatsapp_handler.py`, and a shared
`production/channels/kafka_producer.py`. It also mounts FastAPI webhook endpoints in
`production/api/webhooks.py` and wires the Phase 4B `send_response` stub to dispatch real
messages through the appropriate handler.

**Scope**: 4 new files, 2 updates (tools.py stub → real dispatch, .env.example), 2 test files.
Phase 4C-iii (Web Form) is NOT in scope here.

---

## Technical Context

| Item | Decision |
|------|----------|
| Language | Python 3.12 |
| New dependencies | `aiokafka>=0.11`, `google-api-python-client>=2.0`, `google-auth-oauthlib>=1.0`, `twilio>=9.0`, `fastapi>=0.110`, `uvicorn>=0.29` |
| Kafka client | `aiokafka` — native async, matches existing asyncpg/openai-agents async patterns |
| Kafka topic | `fte.tickets.incoming` (single unified topic per Q1 decision) |
| Webhook framework | FastAPI (already in stack per production/requirements.txt intent) |
| Auth model | Gmail: OAuth2 service-account-style token file; Twilio: HMAC-SHA1 via RequestValidator |
| TicketMessage schema | `src/agent/models.py::TicketMessage` (unchanged; Phase 4C conforms to it) |
| History state | Last seen Gmail `historyId` stored in-memory (module-level var) for hackathon |
| Deduplication | In-memory `set` per handler module; cleared on restart (documented limitation) |

---

## Constitution Check

| Gate | Rule | Status |
|------|------|--------|
| Datetime injection | PKT datetime in all TicketMessage `received_at` fields | ✅ Use `datetime.now(ZoneInfo("Asia/Karachi")).isoformat()` |
| Secrets policy | No hardcoded credentials | ✅ All via `os.environ` |
| Error isolation | Never crash webhook endpoint | ✅ All handlers wrap logic in `try/except` |
| TicketMessage parity | Same schema as prototype | ✅ Import from `src.agent.models` |
| Twilio security | Signature validation on every inbound request | ✅ HTTP 403 on failure |

---

## Project Structure After Phase 4C

```text
production/
├── channels/
│   ├── __init__.py                   (existing)
│   ├── kafka_producer.py             ← NEW: async AIOKafka producer singleton
│   ├── gmail_handler.py              ← REPLACE stub: GmailHandler class
│   ├── whatsapp_handler.py           ← REPLACE stub: WhatsAppHandler class
│   └── web_form_handler.py           (Phase 4C-iii — not in scope)
├── api/
│   ├── __init__.py                   (existing stub)
│   └── webhooks.py                   ← NEW: FastAPI router with 2 POST endpoints
├── agent/
│   └── tools.py                      ← UPDATE: send_response stub → real dispatch
├── tests/
│   ├── test_gmail_handler.py         ← NEW: 10 tests
│   └── test_whatsapp_handler.py      ← NEW: 10 tests
requirements.txt                      ← UPDATE: add aiokafka, google libs, twilio, fastapi
.env.example (root)                   ← UPDATE: add Gmail + Twilio vars
```

---

## Interface Contracts

### Kafka Producer (`kafka_producer.py`)

```
get_kafka_producer() -> AIOKafkaProducer   # lazy singleton, started once
stop_kafka_producer() -> None              # clean shutdown

publish_ticket(message: TicketMessage) -> None
  # serialises TicketMessage to JSON, publishes to fte.tickets.incoming
  # raises KafkaError on failure (caller handles)
```

**Message payload published to Kafka:**
```json
{
  "id": "<uuid>",
  "channel": "email|whatsapp|web_form",
  "customer_email": "<email or null>",
  "customer_phone": "<E.164 or null>",
  "customer_name": "Valued Customer",
  "subject": "<string or null>",
  "message": "<body text>",
  "received_at": "<ISO8601 PKT>",
  "metadata": {
    "thread_id": "<gmail thread id, email only>",
    "message_sid": "<twilio MessageSid, whatsapp only>"
  }
}
```

### Gmail Handler (`gmail_handler.py`)

```
GmailHandler
  setup_credentials() -> None               # loads token from GMAIL_CREDENTIALS_JSON path
  watch_inbox() -> dict                     # calls Gmail API watch(), returns historyId
  process_pub_sub_push(payload: dict) -> None
    # payload: {"message": {"data": "<b64url>", "messageId": "..."}, "subscription": "..."}
    # 1. decode data → {emailAddress, historyId}
    # 2. call history.list(startHistoryId=last_history_id)
    # 3. for each new message: messages.get() → extract headers + body
    # 4. build TicketMessage, dedup check, publish to Kafka
    # 5. update last_history_id
  send_reply(thread_id: str, to_email: str, body: str) -> str
    # sends via Gmail API messages.send with threadId; returns Gmail message id
```

**State**:
- `_seen_message_ids: set[str]` — module-level dedup set
- `_last_history_id: str | None` — last processed historyId; initialised from `watch()` response

### WhatsApp Handler (`whatsapp_handler.py`)

```
WhatsAppHandler
  validate_signature(url: str, post_data: dict, signature: str) -> bool
    # uses twilio.request_validator.RequestValidator(TWILIO_AUTH_TOKEN)
    # returns True if valid; caller raises HTTP 403 on False
  process_webhook(payload: dict) -> TicketMessage | None
    # payload keys: From, Body, MessageSid, NumMedia, ...
    # 1. extract From (strip "whatsapp:" prefix → E.164), Body, MessageSid
    # 2. dedup check on MessageSid; return None if seen
    # 3. handle empty body: set message = "[media attachment — no text]"
    # 4. build TicketMessage, publish to Kafka, return TicketMessage
  send_reply(to_phone: str, body: str) -> str
    # calls twilio REST: client.messages.create(
    #   to=f"whatsapp:{to_phone}", from_=TWILIO_WHATSAPP_NUMBER, body=body[:1600])
    # returns MessageSid
```

**State**:
- `_seen_message_sids: set[str]` — module-level dedup set

### FastAPI Webhooks Router (`api/webhooks.py`)

```
POST /webhooks/gmail      → gmail_webhook(request: Request) -> JSONResponse
  # calls handler.process_pub_sub_push(); always returns 200
  # HTTP 400 on JSON parse error

POST /webhooks/whatsapp   → whatsapp_webhook(request: Request) -> JSONResponse
  # validates signature → 403 on failure
  # calls handler.process_webhook(); returns 200
```

### Updated `send_response` (tools.py)

```
send_response(params: SendResponseInput) -> str
  # channel="email"    → gmail_handler.send_reply(thread_id, to_email, formatted_text)
  # channel="whatsapp" → whatsapp_handler.send_reply(to_phone, formatted_text)
  # channel="web_form" → no-op / API response (Phase 4C-iii)
  # returns {"delivery_status": "delivered"|"failed", "channel": ..., "timestamp": ...}
```

---

## Tasks

### Task 1 — Shared Kafka Producer
**File**: `production/channels/kafka_producer.py`
**Risk**: MEDIUM — new async singleton; must not block event loop

- [ ] 1.1 Implement `get_kafka_producer()` lazy singleton using `AIOKafkaProducer`
- [ ] 1.2 Implement `publish_ticket(message: TicketMessage) -> None` — serialise to JSON, `await producer.send_and_wait(topic, value)`
- [ ] 1.3 Implement `stop_kafka_producer()` for clean shutdown
- [ ] 1.4 `KAFKA_BOOTSTRAP_SERVERS` read from env; raise `EnvironmentError` with clear message if missing
- [ ] 1.5 Log every publish to stderr: `[kafka] published {channel} ticket {id}`

### Task 2 — Gmail Handler ⚠️ HIGH RISK
**File**: `production/channels/gmail_handler.py`
**Risk**: HIGH — OAuth2 credential flow + two-step history.list + historyId state

- [ ] 2.1 `setup_credentials()` — load `GMAIL_CREDENTIALS_JSON` path; build `service = build('gmail', 'v1', credentials=creds)`; catch `FileNotFoundError` and `google.auth.exceptions.TransportError`
- [ ] 2.2 `watch_inbox()` — POST to Gmail watch API with `labelIds=["INBOX"]` and `topicName` from `GOOGLE_CLOUD_PROJECT_ID`; store returned `historyId` as `_last_history_id`
- [ ] 2.3 `process_pub_sub_push(payload)` — decode base64url `message.data`; call `history.list(userId='me', startHistoryId=_last_history_id)`; iterate `messagesAdded` entries
- [ ] 2.4 For each new message: call `messages.get(userId='me', id=msg_id, format='full')`; extract `From` header, `Subject` header, body (prefer `text/plain` part; fallback to snippet)
- [ ] 2.5 Dedup: skip if `msg_id in _seen_message_ids`; add to set on first process
- [ ] 2.6 Build `TicketMessage` from extracted fields (use `src.agent.models.TicketMessage`); publish via `kafka_producer.publish_ticket()`
- [ ] 2.7 Update `_last_history_id` to notification's `historyId` after processing
- [ ] 2.8 `send_reply(thread_id, to_email, body)` — construct MIME message with `threadId`; call `service.users().messages().send(userId='me', body=raw_message)`; return Gmail message id
- [ ] 2.9 All methods wrapped in `try/except Exception`; errors logged to `stderr`; never raise

### Task 3 — WhatsApp Handler ⚠️ HIGH RISK
**File**: `production/channels/whatsapp_handler.py`
**Risk**: HIGH — Twilio signature validation requires exact URL reconstruction; wrong URL = 403 for all real traffic

- [ ] 3.1 `validate_signature(url, post_data, signature)` — `RequestValidator(os.environ["TWILIO_AUTH_TOKEN"]).validate(url, post_data, signature)`; return `bool`
- [ ] 3.2 `process_webhook(payload)` — extract `From` (strip `"whatsapp:"` prefix), `Body`, `MessageSid`, `NumMedia`
- [ ] 3.3 Dedup: skip (return `None`) if `MessageSid in _seen_message_sids`; add on first process
- [ ] 3.4 Empty body handling: if `Body.strip() == ""` and `NumMedia > 0`, set `message = "[media attachment — no text]"`; if `NumMedia == 0` and empty body, set `message = "[empty message]"`
- [ ] 3.5 Build `TicketMessage(channel="whatsapp", customer_phone=from_e164, message=body, ...)`; publish via `kafka_producer.publish_ticket()`
- [ ] 3.6 `send_reply(to_phone, body)` — `client.messages.create(to=f"whatsapp:{to_phone}", from_=TWILIO_WHATSAPP_NUMBER, body=body[:1600])`; return `MessageSid`
- [ ] 3.7 All methods wrapped in `try/except`; errors logged; never raise

### Task 4 — FastAPI Webhook Router ⚠️ HIGH RISK
**File**: `production/api/webhooks.py`
**Risk**: HIGH — URL reconstruction for Twilio signature validation must use `request.url` exactly as Twilio sees it (scheme + host + path); ngrok/proxy headers can break this

- [ ] 4.1 `POST /webhooks/gmail` endpoint — parse JSON body; call `gmail_handler.process_pub_sub_push()`; return `{"status": "ok"}` with HTTP 200; return `{"error": "parse_error"}` with HTTP 400 on bad JSON; never return 5xx
- [ ] 4.2 `POST /webhooks/whatsapp` endpoint — parse form body; extract `X-Twilio-Signature` header; reconstruct full URL as `str(request.url)` for validation; call `whatsapp_handler.validate_signature()`; return HTTP 403 if invalid; call `whatsapp_handler.process_webhook()` if valid; return HTTP 200
- [ ] 4.3 Mount `webhooks.router` in main FastAPI app (creates `production/api/main.py` or updates existing)
- [ ] 4.4 Add `X-Forwarded-Proto` awareness: if running behind a proxy, use `X-Forwarded-Proto` header to reconstruct `https://` URL for Twilio (Twilio always signs with `https`)

### Task 5 — Wire `send_response` in tools.py ⚠️ HIGH RISK
**File**: `production/agent/tools.py` (line ~277 — the stub block)
**Risk**: HIGH — modifies live Phase 4B code that has 122 passing tests; wrong import or error handling change could break existing tests

- [ ] 5.1 Import `GmailHandler` and `WhatsAppHandler` lazily inside `_send_response_impl` (avoid circular import at module level)
- [ ] 5.2 Add `thread_id` and `recipient` to `SendResponseInput` schema in `production/agent/schemas.py` (optional fields; default `None` — backwards compatible)
- [ ] 5.3 Replace stub block: `if channel == "email"` → call `gmail_handler.send_reply(thread_id, customer_email, formatted.formatted_text)`; `if channel == "whatsapp"` → call `whatsapp_handler.send_reply(customer_phone, formatted.formatted_text)`
- [ ] 5.4 Return `{"delivery_status": "delivered", "channel": ..., "timestamp": ...}` on success; `{"delivery_status": "failed", "error": ...}` on exception
- [ ] 5.5 Verify all 122 existing tests still pass after change (tool interface unchanged; only stub block replaced)

### Task 6 — Dependencies & Env Vars
**Files**: `production/requirements.txt`, `.env.example` (root)
**Risk**: LOW

- [ ] 6.1 Add to `production/requirements.txt`:
  - `aiokafka>=0.11`
  - `google-api-python-client>=2.0`
  - `google-auth-oauthlib>=1.0`
  - `google-auth-httplib2>=0.2`
  - `twilio>=9.0`
  - `fastapi>=0.110`
  - `uvicorn>=0.29`
  - `httpx>=0.27` (for FastAPI TestClient in tests)
- [ ] 6.2 Add to `.env.example` (root):
  - `GMAIL_CREDENTIALS_JSON=` (path to OAuth2 credentials JSON file)
  - `GMAIL_USER_EMAIL=support@nexaflow.io`
  - `GOOGLE_CLOUD_PROJECT_ID=`
  - Update existing blank `TWILIO_ACCOUNT_SID=`, `TWILIO_AUTH_TOKEN=`, `TWILIO_WHATSAPP_NUMBER=` with comments

### Task 7 — Gmail Handler Tests
**File**: `production/tests/test_gmail_handler.py`
**Risk**: LOW — all Gmail API calls mocked

- [ ] 7.1 `test_process_pub_sub_push_valid` — mock `history.list` + `messages.get`; assert TicketMessage published to Kafka with `channel="email"`
- [ ] 7.2 `test_process_pub_sub_push_dedup` — send same notification twice; assert `publish_ticket` called exactly once
- [ ] 7.3 `test_process_pub_sub_push_no_new_messages` — `history.list` returns empty `messagesAdded`; assert no Kafka publish, HTTP 200 returned
- [ ] 7.4 `test_send_reply_preserves_thread_id` — mock `messages.send`; assert `threadId` is passed in the request body
- [ ] 7.5 `test_missing_credentials_does_not_crash` — `GMAIL_CREDENTIALS_JSON` unset; assert `setup_credentials()` logs error, does not raise
- [ ] 7.6 `test_base64_decode_error_returns_200` — malformed `data` field in payload; assert endpoint returns 200, error logged
- [ ] 7.7 `test_html_only_email_extracts_snippet` — message with no `text/plain` part; assert `message` field falls back to Gmail `snippet`
- [ ] 7.8 `test_history_list_api_error_does_not_crash` — `history.list` raises `HttpError`; assert endpoint returns 200
- [ ] 7.9 `test_kafka_publish_failure_does_not_crash` — `publish_ticket` raises; assert endpoint returns 200
- [ ] 7.10 `test_ticket_message_schema_matches_prototype` — assert produced TicketMessage passes `isinstance(msg, TicketMessage)` check

### Task 8 — WhatsApp Handler Tests
**File**: `production/tests/test_whatsapp_handler.py`
**Risk**: LOW — Twilio validator and client mocked

- [ ] 8.1 `test_valid_signature_processes_message` — mock `RequestValidator.validate` returns `True`; assert TicketMessage published with `channel="whatsapp"`
- [ ] 8.2 `test_invalid_signature_returns_403` — mock `RequestValidator.validate` returns `False`; assert endpoint returns HTTP 403, no Kafka publish
- [ ] 8.3 `test_missing_signature_header_returns_403` — no `X-Twilio-Signature` header; assert HTTP 403
- [ ] 8.4 `test_duplicate_message_sid_dropped` — same MessageSid posted twice; assert `publish_ticket` called once
- [ ] 8.5 `test_media_only_message_gets_placeholder` — `Body=""`, `NumMedia=1`; assert `message = "[media attachment — no text]"` in TicketMessage
- [ ] 8.6 `test_phone_normalised_strips_whatsapp_prefix` — `From="whatsapp:+12025551234"`; assert `customer_phone="+12025551234"` in TicketMessage
- [ ] 8.7 `test_send_reply_truncates_at_1600_chars` — body with 2000 chars; assert Twilio `create` called with `body` of length 1600
- [ ] 8.8 `test_kafka_publish_failure_returns_200` — `publish_ticket` raises; assert endpoint returns 200
- [ ] 8.9 `test_twilio_client_error_returns_failed_status` — `messages.create` raises; assert `send_reply` returns error dict, no crash
- [ ] 8.10 `test_ticket_message_schema_matches_prototype` — assert produced TicketMessage passes `isinstance(msg, TicketMessage)`

---

## HIGH RISK Summary

| Task | File | Risk | Mitigation |
|------|------|------|------------|
| Task 2 | `gmail_handler.py` | OAuth2 token + history.list state | Mock all Gmail API calls in tests; `_last_history_id` initialised from `watch()` to avoid empty-historyId error |
| Task 3 | `whatsapp_handler.py` | Twilio URL reconstruction for signature | Document exact URL format in code comment; add `test_invalid_signature_returns_403` |
| Task 4 | `api/webhooks.py` | Proxy/ngrok breaks Twilio signature | Task 4.4 handles `X-Forwarded-Proto`; test both `http://` and `https://` in tests |
| Task 5 | `tools.py` | Breaks 122 passing tests | Lazy import + optional `thread_id`/`recipient` fields; run full test suite as acceptance gate |

---

## Risks & Follow-ups

1. **`_last_history_id` process restart**: On restart, the handler has no stored historyId. Calling `watch()` at startup returns a fresh historyId; messages between the last shutdown and restart are silently missed. Acceptable for hackathon; Redis persistence is the production fix.
2. **FastAPI app entrypoint**: `production/api/main.py` may need creating (currently a stub). Task 4.3 covers this but may require deciding on app startup lifecycle (lifespan event for Kafka producer start/stop).
3. **`send_response` schema change**: Adding optional `thread_id` and `recipient` to `SendResponseInput` requires updating both `schemas.py` and any test fixtures that construct `SendResponseInput`. Task 5.5 is the acceptance gate.
