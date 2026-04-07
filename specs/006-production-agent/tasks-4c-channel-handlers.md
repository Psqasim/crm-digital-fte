# Tasks: Phase 4C — Gmail & WhatsApp Channel Handlers

**Input**: `specs/006-production-agent/`
**Branch**: `006-production-agent`
**Plan**: `specs/006-production-agent/plan-4c-channel-handlers.md`
**Spec**: `specs/006-production-agent/spec-4c-channel-handlers.md`
**Phase**: 4C-i (Gmail Handler) + 4C-ii (WhatsApp Handler)
**Phase 4B baseline**: `production/agent/` — 7 tools, 122/122 tests passing

> **Legend**
> - `⚠️ HIGH RISK` — must not break 122 existing tests; run `pytest` after each sub-step
> - `[P]` — parallelisable (different files, no incomplete dependencies)
> - `[US1]` — Email channel (P1); `[US2]` — WhatsApp channel (P1); `[US3]` — Fault isolation (P2)
> - **Recommended order**: T001→T002 → T003–T006 → T007–T026 (or T027–T045) → T043–T049
> - Tests are REQUESTED (Tasks 7 & 8 in plan; spec §"Independent Test" per story)

---

## Phase 1: Setup

**Purpose**: Add new dependencies and env vars; no code logic.

- [ ] T001 Update `production/requirements.txt` — add `aiokafka>=0.11`, `google-api-python-client>=2.0`, `google-auth-oauthlib>=1.0`, `google-auth-httplib2>=0.2`, `twilio>=9.0`, `fastapi>=0.110`, `uvicorn>=0.29`, `httpx>=0.27`
  - **File**: `production/requirements.txt` (UPDATE)
  - **Acceptance**: `pip install -r production/requirements.txt` resolves without conflict; all 8 packages present
  - **Depends on**: None
  - **Test needed**: No
  - **HIGH RISK**: No

- [ ] T002 [P] Update `.env.example` (root) — add `GMAIL_CREDENTIALS_JSON=` (path to token JSON), `GMAIL_USER_EMAIL=support@nexaflow.io`, `GOOGLE_CLOUD_PROJECT_ID=`; annotate existing blank `TWILIO_ACCOUNT_SID=`, `TWILIO_AUTH_TOKEN=`, `TWILIO_WHATSAPP_NUMBER=` with inline comments
  - **File**: `.env.example` (UPDATE)
  - **Acceptance**: File contains all 6 Gmail/Twilio keys; no secrets committed; existing keys preserved
  - **Depends on**: None
  - **Test needed**: No
  - **HIGH RISK**: No

---

## Phase 2: Foundational — Kafka Producer (Blocking)

**Purpose**: Shared async Kafka producer that BOTH Gmail and WhatsApp handlers depend on.
**⚠️ CRITICAL**: Tasks T003–T006 must complete before any channel handler work begins.

- [ ] T003 Create `production/channels/kafka_producer.py` — module scaffold: imports (`aiokafka`, `json`, `os`, `sys`), module-level `_producer: AIOKafkaProducer | None = None`, read `KAFKA_BOOTSTRAP_SERVERS` from env; raise `EnvironmentError` with message `"KAFKA_BOOTSTRAP_SERVERS env var is required"` if missing at first call (not at import time)
  - **File**: `production/channels/kafka_producer.py` (NEW)
  - **Acceptance**: `from production.channels.kafka_producer import get_kafka_producer` imports without error even when `KAFKA_BOOTSTRAP_SERVERS` is unset
  - **Depends on**: T001
  - **Test needed**: No
  - **HIGH RISK**: No

- [ ] T004 Implement `get_kafka_producer() -> AIOKafkaProducer` lazy singleton in `production/channels/kafka_producer.py` — if `_producer` is None: create `AIOKafkaProducer(bootstrap_servers=..., value_serializer=lambda v: json.dumps(v).encode())`, `await producer.start()`, assign to `_producer`; return `_producer`
  - **File**: `production/channels/kafka_producer.py` (UPDATE)
  - **Acceptance**: Second call to `get_kafka_producer()` returns same object (singleton); `start()` called exactly once per process
  - **Depends on**: T003
  - **Test needed**: No
  - **HIGH RISK**: No

- [ ] T005 Implement `publish_ticket(message: TicketMessage) -> None` in `production/channels/kafka_producer.py` — call `await (await get_kafka_producer()).send_and_wait("fte.tickets.incoming", value=message.model_dump())`; log to stderr: `[kafka] published {message.channel} ticket {message.id}`; import `TicketMessage` from `src.agent.models`
  - **File**: `production/channels/kafka_producer.py` (UPDATE)
  - **Acceptance**: `publish_ticket` serialises full TicketMessage dict; topic is exactly `"fte.tickets.incoming"`; log line written to stderr on every call
  - **Depends on**: T004
  - **Test needed**: No
  - **HIGH RISK**: No

- [ ] T006 Implement `stop_kafka_producer() -> None` in `production/channels/kafka_producer.py` — `await _producer.stop()` if `_producer` is not None; reset `_producer = None`; wrap in `try/except Exception` and log; export all three functions in module `__all__`
  - **File**: `production/channels/kafka_producer.py` (UPDATE)
  - **Acceptance**: `stop_kafka_producer()` idempotent (safe to call twice); `_producer` reset to None after stop
  - **Depends on**: T004
  - **Test needed**: No
  - **HIGH RISK**: No

**Checkpoint**: Kafka producer complete. Both channel handlers can now call `publish_ticket()`.

---

## Phase 3: User Story 1 — Email Received, Ticket Queued, Reply Sent (Priority: P1) ⚠️ HIGH RISK

**Goal**: Gmail Pub/Sub push → history.list → TicketMessage on Kafka → threaded reply via Gmail API.

**Independent Test**: POST synthetic Pub/Sub payload to `/webhooks/gmail`. Assert: (a) TicketMessage on `fte.tickets.incoming` with `channel="email"`, (b) `messages.send` called with correct `threadId`, (c) returns HTTP 200.

### Tests for User Story 1 — Gmail Handler (Task 7)

> **Write tests FIRST. All must FAIL before implementation begins.**

- [ ] T007 [P] [US1] Create `production/tests/test_gmail_handler.py` — `test_process_pub_sub_push_valid`: mock `history.list` returning `messagesAdded=[{id: "msg1"}]` and `messages.get` returning headers `[From, Subject]` + plain-text body; mock `publish_ticket`; assert `publish_ticket` called once with `TicketMessage(channel="email")`
  - **File**: `production/tests/test_gmail_handler.py` (NEW)
  - **Acceptance**: Test file importable; `test_process_pub_sub_push_valid` fails with `ImportError` or `AttributeError` before implementation
  - **Depends on**: T006
  - **Test needed**: Yes (this is the test)
  - **HIGH RISK**: No

- [ ] T008 [P] [US1] Add `test_process_pub_sub_push_dedup` in `production/tests/test_gmail_handler.py` — send same Pub/Sub notification (same `historyId` in payload) twice; assert `publish_ticket` called exactly once; second call is a complete no-op
  - **File**: `production/tests/test_gmail_handler.py` (UPDATE)
  - **Acceptance**: `publish_ticket.call_count == 1` after two identical pushes; idempotency confirmed
  - **Depends on**: T007
  - **Test needed**: Yes (this is the test)
  - **HIGH RISK**: No

- [ ] T009 [P] [US1] Add `test_process_pub_sub_push_no_new_messages` in `production/tests/test_gmail_handler.py` — mock `history.list` returns `{"history": [], "historyId": "999"}` (label-change event with no `messagesAdded`); assert `publish_ticket` never called; assert no exception raised
  - **File**: `production/tests/test_gmail_handler.py` (UPDATE)
  - **Acceptance**: `publish_ticket.call_count == 0`; function returns normally
  - **Depends on**: T007
  - **Test needed**: Yes (this is the test)
  - **HIGH RISK**: No

- [ ] T010 [P] [US1] Add `test_send_reply_preserves_thread_id` in `production/tests/test_gmail_handler.py` — mock `service.users().messages().send()`; call `send_reply(thread_id="thread123", to_email="x@y.com", body="Hello")`; assert the raw message body passed to `send()` contains `"threadId": "thread123"`
  - **File**: `production/tests/test_gmail_handler.py` (UPDATE)
  - **Acceptance**: Thread continuity confirmed — `threadId` present in the send payload
  - **Depends on**: T007
  - **Test needed**: Yes (this is the test)
  - **HIGH RISK**: No

- [ ] T011 [P] [US1] Add `test_missing_credentials_does_not_crash` in `production/tests/test_gmail_handler.py` — patch `os.environ` without `GMAIL_CREDENTIALS_JSON`; call `setup_credentials()`; assert no exception raised; assert something written to `sys.stderr`
  - **File**: `production/tests/test_gmail_handler.py` (UPDATE)
  - **Acceptance**: `setup_credentials()` returns normally; error logged; process does not crash
  - **Depends on**: T007
  - **Test needed**: Yes (this is the test)
  - **HIGH RISK**: No

- [ ] T012 [P] [US1] Add `test_base64_decode_error_returns_200` in `production/tests/test_gmail_handler.py` — POST to `/webhooks/gmail` with `{"message": {"data": "!!!invalid_base64!!!", "messageId": "1"}, "subscription": "s"}` via FastAPI `TestClient`; assert HTTP 200; assert error logged to stderr
  - **File**: `production/tests/test_gmail_handler.py` (UPDATE)
  - **Acceptance**: HTTP 200 returned; no 5xx; error in stderr
  - **Depends on**: T007
  - **Test needed**: Yes (this is the test)
  - **HIGH RISK**: No

- [ ] T013 [P] [US1] Add `test_html_only_email_extracts_snippet` in `production/tests/test_gmail_handler.py` — mock `messages.get` returning message with only `text/html` MIME part and `snippet: "Preview text"`; assert produced TicketMessage has `message="Preview text"` (snippet fallback)
  - **File**: `production/tests/test_gmail_handler.py` (UPDATE)
  - **Acceptance**: `ticket.message == "Preview text"`; no crash on missing `text/plain` part
  - **Depends on**: T007
  - **Test needed**: Yes (this is the test)
  - **HIGH RISK**: No

- [ ] T014 [P] [US1] Add `test_history_list_api_error_does_not_crash` in `production/tests/test_gmail_handler.py` — mock `history.list` raises `googleapiclient.errors.HttpError`; POST valid Pub/Sub notification to webhook; assert HTTP 200; assert error logged
  - **File**: `production/tests/test_gmail_handler.py` (UPDATE)
  - **Acceptance**: HTTP 200 returned; no exception propagates from endpoint
  - **Depends on**: T007
  - **Test needed**: Yes (this is the test)
  - **HIGH RISK**: No

- [ ] T015 [P] [US1] Add `test_kafka_publish_failure_does_not_crash` in `production/tests/test_gmail_handler.py` — mock `publish_ticket` raises `Exception("broker unavailable")`; POST valid notification; assert HTTP 200; assert error logged to stderr
  - **File**: `production/tests/test_gmail_handler.py` (UPDATE)
  - **Acceptance**: HTTP 200 returned despite Kafka failure; Pub/Sub retry storm prevented
  - **Depends on**: T007
  - **Test needed**: Yes (this is the test)
  - **HIGH RISK**: No

- [ ] T016 [P] [US1] Add `test_ticket_message_schema_matches_prototype` in `production/tests/test_gmail_handler.py` — call `process_pub_sub_push()` with mocked Gmail API; capture the TicketMessage passed to `publish_ticket`; assert `isinstance(msg, TicketMessage)` and all required fields present (`id`, `channel`, `customer_email`, `message`, `received_at`, `metadata`)
  - **File**: `production/tests/test_gmail_handler.py` (UPDATE)
  - **Acceptance**: `isinstance(msg, TicketMessage) is True`; `msg.channel == "email"`; `msg.metadata.get("thread_id")` is set
  - **Depends on**: T007
  - **Test needed**: Yes (this is the test)
  - **HIGH RISK**: No

### Implementation for User Story 1 — Gmail Handler (Task 2)

- [ ] T017 ⚠️ HIGH RISK [US1] Create `production/channels/gmail_handler.py` — module scaffold: imports (`google-api-python-client`, `google-auth-oauthlib`, `base64`, `json`, `os`, `sys`, `email.mime`, `datetime`, `zoneinfo`); module-level vars `_seen_message_ids: set[str] = set()` and `_last_history_id: str | None = None`; `GmailHandler` class with method stubs; `service: Any = None` instance var
  - **File**: `production/channels/gmail_handler.py` (REPLACE stub)
  - **Acceptance**: File importable; `GmailHandler()` instantiates without error; existing tests still pass (run `pytest production/tests/` — expect 0 new test failures against Phase 4B suite)
  - **Depends on**: T006
  - **Test needed**: No
  - **HIGH RISK**: Yes — replaces stub that Phase 4B imports

- [ ] T018 ⚠️ HIGH RISK [US1] Implement `setup_credentials()` in `production/channels/gmail_handler.py` — read `GMAIL_CREDENTIALS_JSON` path from `os.environ`; load credentials using `google.oauth2.credentials.Credentials.from_authorized_user_file()` or `google.auth.default()`; call `build('gmail', 'v1', credentials=creds)` and assign to `self.service`; catch `FileNotFoundError`, `KeyError`, `google.auth.exceptions.TransportError`; log error to stderr; never raise
  - **File**: `production/channels/gmail_handler.py` (UPDATE)
  - **Acceptance**: Missing `GMAIL_CREDENTIALS_JSON` → logs error, returns None, no exception; valid path → `self.service` is not None; T011 test passes
  - **Depends on**: T017
  - **Test needed**: Yes (T011 covers this)
  - **HIGH RISK**: Yes — OAuth2 credential loading; wrong flow = silent auth failure for all Gmail API calls

- [ ] T019 ⚠️ HIGH RISK [US1] Implement `watch_inbox()` in `production/channels/gmail_handler.py` — call `self.service.users().watches().watch(userId='me', body={"labelIds": ["INBOX"], "topicName": f"projects/{os.environ['GOOGLE_CLOUD_PROJECT_ID']}/topics/gmail-notifications"}).execute()`; store `response["historyId"]` in module-level `_last_history_id`; return full response dict; catch all exceptions and log
  - **File**: `production/channels/gmail_handler.py` (UPDATE)
  - **Acceptance**: `watch_inbox()` sets module-level `_last_history_id` to the value returned by the Gmail API; safe to call when `self.service` is None (logs warning, returns empty dict)
  - **Depends on**: T018
  - **Test needed**: No (mocked in integration; manual verify via ngrok)
  - **HIGH RISK**: Yes — `_last_history_id` initialised here; if None when `process_pub_sub_push` runs, `history.list` will fail silently

- [ ] T020 ⚠️ HIGH RISK [US1] Implement `process_pub_sub_push(payload)` step 1 in `production/channels/gmail_handler.py` — decode `base64.urlsafe_b64decode(payload["message"]["data"] + "==")` → parse JSON → extract `historyId`; **idempotency gate**: if `historyId == _last_history_id`, return immediately (no-op); call `self.service.users().history().list(userId='me', startHistoryId=_last_history_id).execute()`; extract `messagesAdded` list (may be absent → treat as empty)
  - **File**: `production/channels/gmail_handler.py` (UPDATE)
  - **Acceptance**: **Calling with same historyId twice → second call returns immediately without any API call**; `history.list` only called when historyId is new; T008 test passes
  - **Depends on**: T019
  - **Test needed**: Yes (T008 covers dedup; T009 covers empty messagesAdded)
  - **HIGH RISK**: Yes — silent drop risk if historyId state not managed correctly; duplicate processing risk if dedup gate missing

- [ ] T021 ⚠️ HIGH RISK [US1] Implement `process_pub_sub_push(payload)` step 2 in `production/channels/gmail_handler.py` — for each entry in `messagesAdded`: extract `msg_id = entry["message"]["id"]`; skip if `msg_id in _seen_message_ids`; call `messages.get(userId='me', id=msg_id, format='full')`; extract `From` header (parse email address), `Subject` header, body (`text/plain` MIME part → fallback to `snippet`); truncate body to 4000 chars; build `TicketMessage(channel="email", customer_email=from_addr, subject=subject, message=body, received_at=datetime.now(ZoneInfo("Asia/Karachi")).isoformat(), metadata={"thread_id": thread_id})`; call `publish_ticket(ticket)`; add `msg_id` to `_seen_message_ids`; update `_last_history_id = historyId` from notification
  - **File**: `production/channels/gmail_handler.py` (UPDATE)
  - **Acceptance**: Produces TicketMessage with all required fields; `channel="email"`; `metadata["thread_id"]` set; body truncated at 4000 chars; msg_id added to seen set; T007, T013, T016 tests pass
  - **Depends on**: T020
  - **Test needed**: Yes (T007, T013, T016)
  - **HIGH RISK**: Yes — touching TicketMessage schema; wrong field names cause runtime errors invisible without tests

- [ ] T022 [US1] Implement `send_reply(thread_id, to_email, body)` in `production/channels/gmail_handler.py` — construct RFC 2822 email using `email.mime.text.MIMEText`; set `To`, `Subject: Re: [original]`, encode as base64url; call `self.service.users().messages().send(userId='me', body={"raw": encoded, "threadId": thread_id}).execute()`; return Gmail message id from response; catch exceptions and log
  - **File**: `production/channels/gmail_handler.py` (UPDATE)
  - **Acceptance**: `threadId` included in send request body (T010 passes); returns string message id; exception → logs error, returns empty string
  - **Depends on**: T021
  - **Test needed**: Yes (T010)
  - **HIGH RISK**: No

- [ ] T023 [US1] Wrap all `GmailHandler` methods in `try/except Exception` in `production/channels/gmail_handler.py` — each method: catch `Exception as e`; log `[gmail_handler] ERROR in {method_name}: {type(e).__name__}: {e}` to `sys.stderr`; return safe default (None or empty string); NEVER re-raise
  - **File**: `production/channels/gmail_handler.py` (UPDATE)
  - **Acceptance**: Any exception in any method → logged to stderr; method returns safely; T014, T015 tests pass
  - **Depends on**: T022
  - **Test needed**: Yes (T014, T015 cover specific error paths)
  - **HIGH RISK**: No

- [ ] T024 ⚠️ HIGH RISK [US1] Create `production/api/webhooks.py` — `router = APIRouter()`; `POST /webhooks/gmail` endpoint: `async def gmail_webhook(request: Request) -> JSONResponse`; parse JSON body with `try/except json.JSONDecodeError → return JSONResponse({"error": "parse_error"}, status_code=400)`; call `await handler.process_pub_sub_push(body)`; return `JSONResponse({"status": "ok"})` HTTP 200; wrap entire handler body in `try/except Exception → log + return JSONResponse({"status": "error_logged"}, status_code=200)`; NEVER return 5xx
  - **File**: `production/api/webhooks.py` (NEW)
  - **Acceptance**: Valid Pub/Sub payload → HTTP 200; malformed JSON → HTTP 400; any internal exception → HTTP 200 (not 500); T012, T014, T015 tests pass via FastAPI TestClient
  - **Depends on**: T023
  - **Test needed**: Yes (T012, T014, T015)
  - **HIGH RISK**: Yes — this is the public endpoint; 5xx causes Pub/Sub retry storm

- [ ] T025 ⚠️ HIGH RISK [US1] Add `reconstruct_url(request: Request) -> str` helper in `production/api/webhooks.py` — read `X-Forwarded-Proto` header; if present and value is `"https"`, rebuild URL as `f"https://{request.headers['host']}{request.url.path}"`; if `X-Forwarded-Proto` header absent (direct request), return `str(request.url)` unchanged; used by whatsapp endpoint for Twilio signature validation
  - **File**: `production/api/webhooks.py` (UPDATE)
  - **Acceptance**: `reconstruct_url` with `X-Forwarded-Proto: https` → returns `https://...` URL; without header → returns original URL; works for both ngrok proxy and direct local calls
  - **Depends on**: T024
  - **Test needed**: No (exercised by T028 and T029 in Phase 4)
  - **HIGH RISK**: Yes — Twilio always signs with https; wrong scheme = 403 for ALL real traffic

- [ ] T026 [US1] Create `production/api/main.py` (or update existing stub) — `app = FastAPI()`; register `webhooks.router` with `app.include_router(router)`; add lifespan event: `@asynccontextmanager async def lifespan(app)` → `yield` → `await stop_kafka_producer()` on shutdown; set `app = FastAPI(lifespan=lifespan)`
  - **File**: `production/api/main.py` (CREATE or UPDATE stub)
  - **Acceptance**: `uvicorn production.api.main:app --reload` starts without error; `/docs` shows two webhook routes; Kafka producer stopped cleanly on shutdown
  - **Depends on**: T025
  - **Test needed**: No
  - **HIGH RISK**: No

**Checkpoint**: Gmail handler complete. Run `pytest production/tests/test_gmail_handler.py` — all 10 tests must pass.

---

## Phase 4: User Story 2 — WhatsApp Message Received, Ticket Queued, Reply Sent (Priority: P1) ⚠️ HIGH RISK

**Goal**: Twilio webhook → HMAC-SHA1 validation → TicketMessage on Kafka → reply via Twilio REST API.

**Independent Test**: POST synthetic Twilio payload with valid `X-Twilio-Signature` to `/webhooks/whatsapp`. Assert: (a) TicketMessage on `fte.tickets.incoming` with `channel="whatsapp"`, (b) Twilio `messages.create` called with customer's `From` number, (c) HTTP 200.

### Tests for User Story 2 — WhatsApp Handler (Task 8)

> **Write tests FIRST. All must FAIL before implementation begins.**

- [ ] T027 [P] [US2] Create `production/tests/test_whatsapp_handler.py` — `test_valid_signature_processes_message`: mock `RequestValidator.validate` returns `True`; mock `publish_ticket`; POST form payload `{From: "whatsapp:+12025551234", Body: "Hi", MessageSid: "SM123", NumMedia: "0"}`; assert `publish_ticket` called once with `TicketMessage(channel="whatsapp")`; assert HTTP 200
  - **File**: `production/tests/test_whatsapp_handler.py` (NEW)
  - **Acceptance**: Test file importable; `test_valid_signature_processes_message` fails with `ImportError` before implementation; passes after
  - **Depends on**: T006
  - **Test needed**: Yes (this is the test)
  - **HIGH RISK**: No

- [ ] T028 [P] [US2] Add `test_invalid_signature_returns_403` in `production/tests/test_whatsapp_handler.py` — mock `RequestValidator.validate` returns `False`; POST same form payload; assert HTTP 403; assert `publish_ticket` NOT called; assert no TicketMessage produced
  - **File**: `production/tests/test_whatsapp_handler.py` (UPDATE)
  - **Acceptance**: HTTP 403 on invalid signature; `publish_ticket.call_count == 0`
  - **Depends on**: T027
  - **Test needed**: Yes (this is the test)
  - **HIGH RISK**: No

- [ ] T029 [P] [US2] Add `test_missing_signature_header_returns_403` in `production/tests/test_whatsapp_handler.py` — POST without `X-Twilio-Signature` header; assert HTTP 403; assert `publish_ticket` NOT called
  - **File**: `production/tests/test_whatsapp_handler.py` (UPDATE)
  - **Acceptance**: HTTP 403; no TicketMessage; no crash
  - **Depends on**: T027
  - **Test needed**: Yes (this is the test)
  - **HIGH RISK**: No

- [ ] T030 [P] [US2] Add `test_duplicate_message_sid_dropped` in `production/tests/test_whatsapp_handler.py` — POST same `MessageSid="SM123"` twice with valid signature; assert `publish_ticket` called exactly once; second delivery is silent no-op
  - **File**: `production/tests/test_whatsapp_handler.py` (UPDATE)
  - **Acceptance**: `publish_ticket.call_count == 1` after two posts with same MessageSid
  - **Depends on**: T027
  - **Test needed**: Yes (this is the test)
  - **HIGH RISK**: No

- [ ] T031 [P] [US2] Add `test_media_only_message_gets_placeholder` in `production/tests/test_whatsapp_handler.py` — POST `{Body: "", NumMedia: "1", MessageSid: "SM456"}`; assert produced TicketMessage has `message="[media attachment — no text]"`; assert HTTP 200; endpoint does not crash
  - **File**: `production/tests/test_whatsapp_handler.py` (UPDATE)
  - **Acceptance**: `ticket.message == "[media attachment — no text]"`; HTTP 200
  - **Depends on**: T027
  - **Test needed**: Yes (this is the test)
  - **HIGH RISK**: No

- [ ] T032 [P] [US2] Add `test_phone_normalised_strips_whatsapp_prefix` in `production/tests/test_whatsapp_handler.py` — POST `{From: "whatsapp:+12025551234", Body: "test", MessageSid: "SM789"}`; assert produced TicketMessage has `customer_phone="+12025551234"` (prefix stripped)
  - **File**: `production/tests/test_whatsapp_handler.py` (UPDATE)
  - **Acceptance**: `ticket.customer_phone == "+12025551234"`; "whatsapp:" prefix absent
  - **Depends on**: T027
  - **Test needed**: Yes (this is the test)
  - **HIGH RISK**: No

- [ ] T033 [P] [US2] Add `test_send_reply_truncates_at_1600_chars` in `production/tests/test_whatsapp_handler.py` — mock `twilio_client.messages.create`; call `send_reply(to_phone="+1234", body="x" * 2000)`; assert `create` called with `body` of `len == 1600`
  - **File**: `production/tests/test_whatsapp_handler.py` (UPDATE)
  - **Acceptance**: `len(create_call_kwargs["body"]) == 1600`; body[:1600] applied
  - **Depends on**: T027
  - **Test needed**: Yes (this is the test)
  - **HIGH RISK**: No

- [ ] T034 [P] [US2] Add `test_kafka_publish_failure_returns_200` in `production/tests/test_whatsapp_handler.py` — mock `publish_ticket` raises `Exception`; POST valid Twilio payload with valid signature; assert HTTP 200; assert error logged to stderr
  - **File**: `production/tests/test_whatsapp_handler.py` (UPDATE)
  - **Acceptance**: HTTP 200 despite Kafka failure; Twilio retry storm prevented
  - **Depends on**: T027
  - **Test needed**: Yes (this is the test)
  - **HIGH RISK**: No

- [ ] T035 [P] [US2] Add `test_twilio_client_error_returns_failed_status` in `production/tests/test_whatsapp_handler.py` — mock `messages.create` raises `TwilioException`; call `send_reply("+1234", "Hello")`; assert returns dict with `delivery_status="failed"`; assert no exception propagates
  - **File**: `production/tests/test_whatsapp_handler.py` (UPDATE)
  - **Acceptance**: `result["delivery_status"] == "failed"`; no crash; error logged
  - **Depends on**: T027
  - **Test needed**: Yes (this is the test)
  - **HIGH RISK**: No

- [ ] T036 [P] [US2] Add `test_ticket_message_schema_matches_prototype` in `production/tests/test_whatsapp_handler.py` — mock all external calls; run `process_webhook()`; capture TicketMessage passed to `publish_ticket`; assert `isinstance(msg, TicketMessage)` and `msg.channel == "whatsapp"` and `msg.metadata.get("message_sid")` is set
  - **File**: `production/tests/test_whatsapp_handler.py` (UPDATE)
  - **Acceptance**: `isinstance(msg, TicketMessage) is True`; `msg.channel == "whatsapp"`; `msg.metadata["message_sid"]` present
  - **Depends on**: T027
  - **Test needed**: Yes (this is the test)
  - **HIGH RISK**: No

### Implementation for User Story 2 — WhatsApp Handler (Task 3)

- [ ] T037 ⚠️ HIGH RISK [US2] Create `production/channels/whatsapp_handler.py` — module scaffold: imports (`twilio.rest`, `twilio.request_validator`, `os`, `sys`, `datetime`, `zoneinfo`, `uuid`); module-level `_seen_message_sids: set[str] = set()`; read `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_NUMBER` from `os.environ` with `.get()` (None if missing — log warning at first actual API call, NOT at import); `WhatsAppHandler` class with method stubs; `twilio_client = Client(account_sid, auth_token)` lazily initialised in `__init__`
  - **File**: `production/channels/whatsapp_handler.py` (REPLACE stub)
  - **Acceptance**: File importable without env vars set; `WhatsAppHandler()` instantiates without error; no crash at import time; existing 122 tests unaffected
  - **Depends on**: T006
  - **Test needed**: No
  - **HIGH RISK**: Yes — replaces stub; circular import risk if handlers import each other

- [ ] T038 ⚠️ HIGH RISK [US2] Implement `validate_signature(url, post_data, signature)` in `production/channels/whatsapp_handler.py` — `RequestValidator(os.environ.get("TWILIO_AUTH_TOKEN", "")).validate(url, post_data, signature)`; return `bool`; catch `KeyError` on missing env var → log warning, return `False`; NEVER raise
  - **File**: `production/channels/whatsapp_handler.py` (UPDATE)
  - **Acceptance**: Valid Twilio test credentials + correct URL → `True`; wrong signature → `False`; missing env var → `False` (not exception); T028, T029 tests pass
  - **Depends on**: T037
  - **Test needed**: Yes (T028, T029)
  - **HIGH RISK**: Yes — HMAC-SHA1 validation requires EXACT URL match (scheme + host + path + query); any mismatch = 403 for all real traffic

- [ ] T039 [US2] Implement `process_webhook(payload: dict) -> TicketMessage | None` in `production/channels/whatsapp_handler.py` — extract `From = payload.get("From", "").replace("whatsapp:", "")` → E.164 phone; `Body = payload.get("Body", "").strip()`; `MessageSid = payload["MessageSid"]`; `NumMedia = int(payload.get("NumMedia", "0"))`; dedup: return `None` if `MessageSid in _seen_message_sids`; empty body: `message = "[media attachment — no text]"` if `NumMedia > 0` else `"[empty message]"`; build `TicketMessage(channel="whatsapp", customer_phone=from_e164, message=message_text, received_at=datetime.now(ZoneInfo("Asia/Karachi")).isoformat(), metadata={"message_sid": MessageSid})`; call `publish_ticket(ticket)`; add `MessageSid` to `_seen_message_sids`; return ticket
  - **File**: `production/channels/whatsapp_handler.py` (UPDATE)
  - **Acceptance**: T027, T030, T031, T032 pass; `customer_phone` has no "whatsapp:" prefix; dedup returns None on second call; media placeholder set correctly
  - **Depends on**: T038
  - **Test needed**: Yes (T027, T030, T031, T032)
  - **HIGH RISK**: No

- [ ] T040 [US2] Implement `send_reply(to_phone, body)` in `production/channels/whatsapp_handler.py` — `self.twilio_client.messages.create(to=f"whatsapp:{to_phone}", from_=os.environ.get("TWILIO_WHATSAPP_NUMBER", ""), body=body[:1600])`; return `message.sid`; catch `TwilioException` → log error, return `{"delivery_status": "failed", "error": str(e)}`; catch all other exceptions → same
  - **File**: `production/channels/whatsapp_handler.py` (UPDATE)
  - **Acceptance**: Body truncated to 1600 chars (T033 passes); Twilio error → returns failed dict, no crash (T035 passes); success → returns MessageSid string
  - **Depends on**: T039
  - **Test needed**: Yes (T033, T035)
  - **HIGH RISK**: No

- [ ] T041 [US2] Wrap all `WhatsAppHandler` methods in `try/except Exception` in `production/channels/whatsapp_handler.py` — catch `Exception as e`; log `[whatsapp_handler] ERROR in {method_name}: {type(e).__name__}: {e}` to `sys.stderr`; return safe default; NEVER re-raise
  - **File**: `production/channels/whatsapp_handler.py` (UPDATE)
  - **Acceptance**: T034 passes; any exception → logged to stderr; method returns safely
  - **Depends on**: T040
  - **Test needed**: Yes (T034)
  - **HIGH RISK**: No

- [ ] T042 ⚠️ HIGH RISK [US2] Add `POST /webhooks/whatsapp` endpoint to `production/api/webhooks.py` — `async def whatsapp_webhook(request: Request) -> JSONResponse`; parse form body `await request.form()`; extract `X-Twilio-Signature` header → return HTTP 403 if absent; reconstruct URL via `reconstruct_url(request)` (uses `X-Forwarded-Proto` for https); call `whatsapp_handler.validate_signature(url, dict(form_data), signature)` → return HTTP 403 if False; call `whatsapp_handler.process_webhook(dict(form_data))`; return HTTP 200; wrap all in `try/except Exception → log + HTTP 200`; NEVER return 5xx
  - **File**: `production/api/webhooks.py` (UPDATE)
  - **Acceptance**: Valid signature → HTTP 200; invalid signature → HTTP 403; missing header → HTTP 403; Kafka failure → HTTP 200; T027–T034 endpoint tests pass
  - **Depends on**: T041, T025
  - **Test needed**: Yes (T027–T034)
  - **HIGH RISK**: Yes — URL for `validate_signature` MUST match exactly what Twilio used when signing; `reconstruct_url()` must produce `https://` when behind ngrok/proxy

**Checkpoint**: WhatsApp handler complete. Run `pytest production/tests/test_whatsapp_handler.py` — all 10 tests must pass.

---

## Phase 5: User Story 3 — Handler Fault Isolation (Priority: P2)

**Goal**: Any internal error → logged to stderr, webhook returns 200 or 400 (never 500).

**Independent Test**: Mock Kafka producer to raise; assert both `/webhooks/gmail` and `/webhooks/whatsapp` still return HTTP 200.

- [ ] T043 [US3] Audit `production/api/webhooks.py` gmail endpoint — confirm all 3 error paths return correct codes: (a) malformed JSON → HTTP 400 `{"error": "parse_error"}`; (b) Gmail API error → HTTP 200 `{"status": "error_logged"}`; (c) Kafka publish failure → HTTP 200; add any missing `try/except` blocks
  - **File**: `production/api/webhooks.py` (UPDATE if gaps found)
  - **Acceptance**: T012, T014, T015 all pass; no HTTP 5xx reachable through any exception path
  - **Depends on**: T024
  - **Test needed**: Yes (T012, T014, T015 verify this)
  - **HIGH RISK**: No

- [ ] T044 [US3] Audit `production/api/webhooks.py` whatsapp endpoint — confirm error paths: (a) invalid signature → HTTP 403; (b) missing header → HTTP 403; (c) Kafka failure → HTTP 200; (d) Twilio client error → HTTP 200; add any missing guards
  - **File**: `production/api/webhooks.py` (UPDATE if gaps found)
  - **Acceptance**: T028, T029, T034 all pass; no HTTP 5xx reachable through any exception path
  - **Depends on**: T042
  - **Test needed**: Yes (T028, T029, T034)
  - **HIGH RISK**: No

- [ ] T045 [US3] Run full Phase 4B regression: `pytest production/tests/ -v --tb=short` — confirm all 122 existing tests still pass; any failure is a blocker before proceeding to Phase 6
  - **File**: `production/tests/` (READ-ONLY check)
  - **Acceptance**: `122 passed, 0 failed`; all new tests run as additive; no regressions
  - **Depends on**: T044
  - **Test needed**: Yes (regression gate)
  - **HIGH RISK**: No

**Checkpoint**: All 3 user stories complete. Run full suite: `pytest production/tests/ -v` — all tests (122 + 20 new) pass.

---

## Phase 6: Polish & Cross-Cutting — Wire `send_response` (Task 5)

**Purpose**: Replace the `send_response` stub in Phase 4B `tools.py` with real dispatch.
**⚠️ CRITICAL**: Any change to `tools.py` or `schemas.py` risks breaking the 122-test suite.

- [ ] T046 ⚠️ HIGH RISK Update `production/agent/schemas.py` — add two optional fields to `SendResponseInput`: `thread_id: str | None = Field(default=None, description="Gmail threadId for email replies; required when channel=email")` and `recipient: str | None = Field(default=None, description="Override recipient; uses ticket customer_email/phone if None")`; backwards compatible (both default None; existing tests pass unchanged)
  - **File**: `production/agent/schemas.py` (UPDATE)
  - **Acceptance**: All existing `SendResponseInput` constructors still valid; `SendResponseInput.model_json_schema()` shows two new optional fields; run `pytest production/tests/ -v` — 122 passed
  - **Depends on**: T045
  - **Test needed**: No (regression gate is T047's pytest run)
  - **HIGH RISK**: Yes — any change to Pydantic schema field types or validators can break existing tests silently

- [ ] T047 ⚠️ HIGH RISK Update `production/agent/tools.py` `_send_response_impl` — add lazy imports INSIDE the function body (not at module top): `from production.channels.gmail_handler import GmailHandler` and `from production.channels.whatsapp_handler import WhatsAppHandler`; replace stub block with channel routing: `if params.channel == "email": handler = GmailHandler(); handler.setup_credentials(); result = handler.send_reply(thread_id=params.thread_id, to_email=..., body=formatted.formatted_text)` and `elif params.channel == "whatsapp": handler = WhatsAppHandler(); result = handler.send_reply(to_phone=..., body=formatted.formatted_text)`; `else: result = "[web_form: no outbound — Phase 4C-iii]"` 
  - **File**: `production/agent/tools.py` (UPDATE — stub block at line ~277)
  - **Acceptance**: Lazy imports do not cause circular import (`python -c "from production.agent.tools import *"` runs without error); `web_form` channel still returns a non-crashing value; function interface (`SendResponseInput` → `str`) unchanged
  - **Depends on**: T046
  - **Test needed**: No (regression gate is T048's pytest run)
  - **HIGH RISK**: Yes — modifies live Phase 4B code; lazy import pattern required to avoid circular dependency (`tools.py` → `gmail_handler.py` → `kafka_producer.py` → `models.py` → back)

- [ ] T048 ⚠️ HIGH RISK Update `_send_response_impl` return value in `production/agent/tools.py` — on success: return `json.dumps({"delivery_status": "delivered", "channel": params.channel, "timestamp": datetime.now(ZoneInfo("Asia/Karachi")).isoformat()})`; on any exception from handler: catch `Exception as e`, log to stderr, return `json.dumps({"delivery_status": "failed", "error": str(e), "channel": params.channel})`; wrap entire routing block in `try/except`
  - **File**: `production/agent/tools.py` (UPDATE)
  - **Acceptance**: Return value is always valid JSON string; `delivery_status` is `"delivered"` or `"failed"`; any channel handler error → failed status, not exception propagation
  - **Depends on**: T047
  - **Test needed**: No (regression gate is T049's pytest run)
  - **HIGH RISK**: Yes — return type change could break test assertions on `send_response` output

- [ ] T049 ⚠️ HIGH RISK Run `pytest production/tests/ -v --tb=short` after all `tools.py` changes — MUST show 122 passed with 0 failures; if any test fails, revert the relevant change and fix before continuing
  - **File**: `production/tests/` (READ-ONLY gate)
  - **Acceptance**: **122 passed, 0 failed** — this is the acceptance gate for all Phase 6 changes; commit only after this passes
  - **Depends on**: T048
  - **Test needed**: Yes (regression gate)
  - **HIGH RISK**: Yes — commit gate; do not proceed to git commit until this is green

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — T001, T002 can start immediately and in parallel
- **Foundational (Phase 2)**: Depends on T001; T003→T004→T005→T006 must run sequentially (each builds on previous)
- **US1 (Phase 3)**: Depends on Foundational (T006); tests T007–T016 parallelisable with each other; implementation T017→T018→T019→T020→T021→T022→T023→T024→T025→T026 sequential
- **US2 (Phase 4)**: Depends on Foundational (T006); tests T027–T036 parallelisable; implementation T037→T038→T039→T040→T041→T042 sequential; T042 also depends on T025 (reconstruct_url)
- **US3 (Phase 5)**: Depends on US1 and US2 complete; T043→T044→T045 sequential
- **Polish (Phase 6)**: Depends on T045 passing; T046→T047→T048→T049 sequential

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 2 — no dependency on US2
- **US2 (P1)**: Can start after Phase 2 — no dependency on US1 (except T042 needs T025 from US1's webhook file)
- **US3 (P2)**: Depends on both US1 and US2 complete

### Parallel Opportunities

```bash
# Phase 1 — parallel
T001 (requirements.txt)  ||  T002 (.env.example)

# Phase 3 tests — all parallel after T006
T007 || T008 || T009 || T010 || T011 || T012 || T013 || T014 || T015 || T016

# Phase 4 tests — all parallel after T006
T027 || T028 || T029 || T030 || T031 || T032 || T033 || T034 || T035 || T036

# US1 and US2 implementation — parallel after Phase 2 (different files)
[T017-T023 gmail_handler.py]  ||  [T037-T041 whatsapp_handler.py]
```

---

## HIGH RISK Summary

| Task | File | Risk | Acceptance Criteria |
|------|------|------|---------------------|
| T020 | `gmail_handler.py` process_pub_sub_push step 1 | historyId idempotency — silent drop risk | Same historyId twice → second call returns immediately; T008 passes |
| T021 | `gmail_handler.py` process_pub_sub_push step 2 | TicketMessage field mismatch | T007, T013, T016 pass; `channel="email"`; `metadata["thread_id"]` set |
| T024 | `api/webhooks.py` gmail endpoint | 5xx causes Pub/Sub retry storm | Malformed JSON → 400; all other errors → 200; never 5xx |
| T025 | `api/webhooks.py` reconstruct_url | Wrong scheme breaks ALL Twilio validation | `X-Forwarded-Proto: https` → returns `https://...` URL |
| T038 | `whatsapp_handler.py` validate_signature | HMAC-SHA1 exact URL match | Valid credentials → True; wrong signature → False; missing env → False (not exception) |
| T042 | `api/webhooks.py` whatsapp endpoint | URL mismatch = 403 for ALL real traffic | T027–T034 pass; valid sig → 200; invalid sig → 403; Kafka failure → 200 |
| T046 | `schemas.py` | Schema change breaks 122 tests | `pytest production/tests/ -v` — 122 passed after change |
| T047 | `tools.py` lazy imports | Circular import at module load | `python -c "from production.agent.tools import *"` succeeds; 122 tests pass |
| T048 | `tools.py` return value | Return type change breaks test assertions | Return is always valid JSON string; 122 tests pass |
| T049 | `production/tests/` regression gate | Commit gate | **122 passed, 0 failed** — hard stop |

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1 + Phase 2 (T001–T006)
2. Complete Phase 3 US1 (T007–T026) — Gmail handler + webhook endpoint
3. **STOP and VALIDATE**: `pytest production/tests/test_gmail_handler.py` — 10/10 pass
4. Optionally demo: POST synthetic Pub/Sub to local server, verify Kafka publish

### Incremental Delivery

1. Phase 1 + Phase 2 → Kafka producer ready
2. Phase 3 → Gmail handler live → test independently
3. Phase 4 → WhatsApp handler live → test independently
4. Phase 5 → Fault isolation verified → full regression (122 + 20 = 142 tests)
5. Phase 6 → `send_response` wired → final regression (142 tests)

---

## Notes

- `[P]` tasks = different files, no cross-dependencies; safe to run in parallel
- `[US1/US2/US3]` maps to user story for traceability
- Commit after T026 (US1 complete), after T042 (US2 complete), after T045 (US3 complete), after T049 (Polish complete)
- Do NOT push until all phases complete and T049 is green
- If T049 fails: isolate which Phase 6 task caused the regression; revert that task; fix; re-run T049
