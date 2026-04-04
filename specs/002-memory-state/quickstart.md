# Quickstart — Memory & State Integration (Phase 2C)

**Date**: 2026-04-02  
**Branch**: `002-memory-state`

---

## What Changes in prototype.py

`process_ticket` gains two store interaction points — one before KB search (load context) and one after response generation (record state). All other steps are unchanged.

```python
# NEW import at top of prototype.py
from src.agent.conversation_store import get_store

def process_ticket(msg: TicketMessage) -> AgentResponse:
    store = get_store()                          # singleton

    # Step 1: Normalize (unchanged)
    ticket = normalize_message(msg)

    # ── NEW: Step 1b — Resolve identity + load history ────────────────
    customer_key = store.resolve_identity(
        email=ticket.customer_email,
        phone=ticket.customer_phone,
    )
    customer = store.get_or_create_customer(
        key=customer_key,
        name=ticket.customer_name,
        channel=ticket.channel.value,
    )
    conversation = store.get_or_create_conversation(
        customer_key=customer_key,
        channel=ticket.channel.value,
    )
    conversation_context = store.get_conversation_context(customer_key)
    prior_topic = store.has_prior_topic(customer_key, ticket.inferred_topic)
    # ──────────────────────────────────────────────────────────────────

    # Step 2: KB search (unchanged in call; context injected below)
    kb_results = _kb.search(ticket.inferred_topic + " " + ticket.message[:200])

    # Step 3: Escalation (unchanged)
    escalation = evaluate_escalation(ticket.message)

    # Step 4: Escalation short-circuit (unchanged structure, +store write)
    if escalation.should_escalate:
        raw = _ESCALATION_ACK_TEMPLATE
        formatted = format_response(raw, ticket.channel, ticket.customer_first_name)
        elapsed = time.monotonic() * 1000 - start_ms
        dt_str = ...

        # ── NEW: record inbound + outbound, transition ticket ─────────
        inbound_msg = _make_message(ticket, "inbound", escalation)
        store.add_message(conversation.id, inbound_msg)
        store.add_topic(conversation.id, ticket.inferred_topic)
        store.transition_ticket(conversation.id, TicketStatus.ESCALATED)
        outbound_msg = _make_message_outbound(raw, ticket.channel, dt_str)
        store.add_message(conversation.id, outbound_msg)
        # ─────────────────────────────────────────────────────────────

        return AgentResponse(...)

    # Step 5: Generate response (context-enriched prompt)
    system_prompt = get_system_prompt(ticket.channel.value, ticket.customer_first_name)

    # ── NEW: inject conversation history + prior-topic hint ───────────
    prior_note = ""
    if prior_topic:
        count = store.count_topic_contacts(customer_key, ticket.inferred_topic)
        prior_note = (
            f"\n\nNote: This customer has contacted us about '{ticket.inferred_topic}' "
            f"{count} time(s) before. Skip basic steps already attempted."
        )
    history_note = f"\n\nConversation so far:\n{conversation_context}" if conversation_context else ""
    # ─────────────────────────────────────────────────────────────────

    user_content = ticket.message
    if kb_context:
        user_content = (
            f"Knowledge base context:\n{kb_context}"
            f"{history_note}{prior_note}\n\n---\nCustomer message:\n{ticket.message}"
        )

    # ... OpenAI call unchanged ...

    # ── NEW: record state after generation ───────────────────────────
    inbound_msg = _make_message(ticket, "inbound", escalation)
    store.add_message(conversation.id, inbound_msg)
    store.add_topic(conversation.id, ticket.inferred_topic)
    store.transition_ticket(conversation.id, TicketStatus.PENDING)
    outbound_msg = _make_message_outbound(raw_response, ticket.channel, dt_str)
    store.add_message(conversation.id, outbound_msg)
    # ─────────────────────────────────────────────────────────────────

    return AgentResponse(...)
```

---

## New File: src/agent/conversation_store.py

Single new module. Implements `ConversationStore` per the interface in
`specs/002-memory-state/contracts/store_interface.py`.

```
src/agent/
├── models.py                 # existing — add TicketStatus, SentimentLabel, SentimentTrend
├── conversation_store.py     # NEW — ConversationStore + get_store()
├── prototype.py              # modified — two store interaction points
├── prompts.py                # unchanged
├── knowledge_base.py         # unchanged
├── escalation_evaluator.py   # unchanged
└── channel_formatter.py      # unchanged
```

---

## Sentinel Constants (in conversation_store.py)

```python
MESSAGE_CAP = 20
SENTIMENT_WINDOW = 3
URGENCY_SCORE_MAP = {
    ("high", True):   0.05,
    ("normal", True): 0.25,
    ("low", True):    0.45,
    (None, False):    0.80,   # no escalation
}
```

---

## Test Pattern

```python
# tests/unit/test_conversation_store.py

from src.agent.conversation_store import ConversationStore

def make_store() -> ConversationStore:
    return ConversationStore()   # fresh instance per test — NOT the singleton

def test_resolve_identity_email_only():
    store = make_store()
    key = store.resolve_identity(email="alice@ex.com", phone=None)
    assert key == "alice@ex.com"

def test_resolve_identity_phone_mapped():
    store = make_store()
    store.link_phone_to_email("+923001234567", "alice@ex.com")
    key = store.resolve_identity(email=None, phone="+923001234567")
    assert key == "alice@ex.com"

def test_message_cap_enforced():
    store = make_store()
    store.get_or_create_customer("alice@ex.com", "Alice", "email")
    conv = store.get_or_create_conversation("alice@ex.com", "email")
    for i in range(21):
        store.add_message(conv.id, _make_msg(f"msg {i}"))
    assert len(conv.messages) == 20
    assert conv.messages[0].text == "msg 1"   # msg 0 was dropped

def test_ticket_resolved_opens_new_conversation():
    store = make_store()
    store.get_or_create_customer("alice@ex.com", "Alice", "email")
    conv1 = store.get_or_create_conversation("alice@ex.com", "email")
    store.transition_ticket(conv1.id, TicketStatus.PENDING)
    store.transition_ticket(conv1.id, TicketStatus.RESOLVED)
    conv2 = store.get_or_create_conversation("alice@ex.com", "email")
    assert conv1.id != conv2.id
```

---

## Running All Tests

```bash
# All 16 Phase 2B tests must still pass
pytest tests/test_core_loop.py tests/test_escalation_evaluator.py tests/test_prototype.py -v

# New Phase 2C tests
pytest tests/unit/test_conversation_store.py -v
```

No new external services are required. `conversation_store.py` has zero external imports beyond Python stdlib and `src.agent.models`.
