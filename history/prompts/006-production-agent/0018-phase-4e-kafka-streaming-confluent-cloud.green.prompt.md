---
id: "0018"
title: Phase 4E Kafka Streaming Confluent Cloud
stage: green
date: 2026-04-08
surface: agent
model: claude-sonnet-4-6
feature: 006-production-agent
branch: 008-kafka-streaming
user: Muhammad Qasim
command: /sp.implement
labels: ["kafka","confluent-cloud","streaming","consumer","producer","phase-4e"]
links:
  spec: null
  ticket: null
  adr: null
  pr: https://github.com/Psqasim/crm-digital-fte/pull/6
files:
  - production/channels/kafka_producer.py
  - production/kafka/__init__.py
  - production/kafka/consumer.py
  - production/kafka/setup_topics.py
  - production/requirements.txt
  - production/workers/message_processor.py
  - production/tests/test_kafka.py
tests:
  - production/tests/test_kafka.py::TestProducerConfig::test_config_contains_all_required_keys
  - production/tests/test_kafka.py::TestProducerConfig::test_config_uses_sasl_ssl_not_plaintext
  - production/tests/test_kafka.py::TestPublishTicket::test_returns_false_when_producer_raises
  - production/tests/test_kafka.py::TestPublishTicket::test_returns_false_when_flush_raises
  - production/tests/test_kafka.py::TestPublishTicket::test_returns_true_on_success
  - production/tests/test_kafka.py::TestPublishTicket::test_produce_uses_ticket_id_as_key
  - production/tests/test_kafka.py::TestPublishTicket::test_produce_default_topic_is_incoming
  - production/tests/test_kafka.py::TestConsumerMessageParsing::test_handle_message_calls_httpx_post
  - production/tests/test_kafka.py::TestConsumerMessageParsing::test_handle_message_skips_missing_ticket_id
  - production/tests/test_kafka.py::TestConsumerMessageParsing::test_handle_message_survives_httpx_error
  - production/tests/test_kafka.py::TestConsumerMessageParsing::test_get_consumer_config_keys
  - production/tests/test_kafka.py::TestDeliveryReport::test_delivery_report_on_error
  - production/tests/test_kafka.py::TestDeliveryReport::test_delivery_report_on_success
---

## Prompt

 ## CONTEXT
Project: CRM Digital FTE Factory — GIAIC Hackathon 5
Location: /home/ps_qasim/projects/crm-digital-fte
Phase: 4E — Kafka Event Streaming

Confluent Cloud cluster already created:
- Cluster: nexaflow-dev (lkc-jkm90w), AWS ap-south-1 (Mumbai)
- Existing topic: support-tickets
- Credentials already in .env:
  KAFKA_BOOTSTRAP_SERVERS, KAFKA_API_KEY, KAFKA_API_SECRET, KAFKA_TOPIC

Current state: kafka_producer.py exists but uses wrong config.
Worker polls via httpx every 30s — stays as fallback.

## MANDATORY — USE CONTEXT7 BEFORE ANY CODE
Search:
1. "confluent-kafka python producer SASL_SSL config"
2. "confluent-kafka python consumer poll subscribe"
Do NOT write code until confirmed.

## TASK
Create branch: 008-kafka-streaming from main

### Step 1: Install confluent-kafka
pip install confluent-kafka --break-system-packages
Add confluent-kafka>=2.3.0 to production/requirements.txt

### Step 2: Create remaining Kafka topics
production/kafka/setup_topics.py — create these via AdminClient:
- fte.tickets.incoming (rename/alias for support-tickets)
- fte.tickets.processed
- fte.escalations
- fte.metrics

### Step 3: Update production/channels/kafka_producer.py
Replace with confluent-kafka Producer using SASL_SSL config.

### Step 4: production/kafka/consumer.py
Kafka consumer subscribing to fte.tickets.incoming, calling /agent/process/<ticket_id>.

### Step 5: Update production/workers/message_processor.py
Primary = Kafka consumer, fallback = httpx polling.

### Step 6: Smoke test
### Step 7: Tests — production/tests/test_kafka.py
### Step 8: Commit, push, PR, merge via GitHub MCP

## RULES
- confluent-kafka (not aiokafka)
- Kafka publish always best-effort — never crash the app
- Run pytest after implementation

## Response snapshot

Phase 4E implemented end-to-end:

1. **Context7 confirmed** — SASL_SSL config validated against confluent-kafka-python docs before writing code.

2. **Branch**: `008-kafka-streaming` created from main.

3. **confluent-kafka 2.14.0** installed via `uv pip install` (venv uses uv, not pip). Added `confluent-kafka>=2.3.0` to `production/requirements.txt`.

4. **production/kafka/** created:
   - `__init__.py` — package marker
   - `setup_topics.py` — AdminClient creates `fte.tickets.incoming`, `fte.tickets.processed`, `fte.escalations`, `fte.metrics` (3 partitions, RF=3 for tickets; 1 partition for escalations/metrics)
   - `consumer.py` — blocking consumer loop, SASL_SSL/PLAIN, group `nexaflow-fte-consumer`, calls `/agent/process/<ticket_id>` via httpx; PARTITION_EOF handled; never crashes

5. **production/channels/kafka_producer.py** — replaced aiokafka singleton with confluent-kafka `Producer`. `publish_ticket()` is best-effort (returns False on any error). `stop_kafka_producer()` kept as no-op for API backward compatibility.

6. **production/workers/message_processor.py** — if `KAFKA_BOOTSTRAP_SERVERS` is set, runs Kafka consumer; otherwise falls back to httpx polling loop.

7. **Tests** — 13 new tests in `test_kafka.py`; 62 passed / 19 skipped / 0 failed total.

8. **PR #6** created and merged to main: https://github.com/Psqasim/crm-digital-fte/pull/6

## Outcome

- ✅ Impact: Confluent Cloud Kafka streaming fully wired — producer (SASL_SSL), consumer, topic setup, worker fallback
- 🧪 Tests: 62 passed, 19 skipped, 0 failed (13 new kafka tests)
- 📁 Files: 7 files created/modified
- 🔁 Next prompts: Phase 4F — Docker + Kubernetes
- 🧠 Reflection: aiokafka was incompatible with Confluent Cloud SASL_SSL; confluent-kafka is the correct library. uv is the package manager (not pip/pip3).

## Evaluation notes (flywheel)

- Failure modes observed: `stop_kafka_producer` import error from `production/api/main.py` — fixed by adding no-op shim; pip/pip3 not available — used `uv pip install`
- Graders run and results (PASS/FAIL): pytest 62 PASS / 0 FAIL
- Prompt variant (if applicable): phase-4e-kafka-streaming-v1
- Next experiment: Add Kafka consumer as a separate Docker service in Phase 4F
