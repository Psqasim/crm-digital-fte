"""
production/kafka/consumer.py
Phase 4E: Confluent Cloud Kafka consumer — triggers agent processing per ticket.

Subscribes to 'fte.tickets.incoming', calls /agent/process/<ticket_id> on each
message. Never crashes; all errors are logged and the loop continues.

Usage:
    python -m production.kafka.consumer
    # or from message_processor when KAFKA_BOOTSTRAP_SERVERS is set
"""

from __future__ import annotations

import json
import os
import sys

import httpx
from confluent_kafka import Consumer, KafkaError


def get_consumer_config() -> dict:
    return {
        "bootstrap.servers": os.environ["KAFKA_BOOTSTRAP_SERVERS"],
        "security.protocol": "SASL_SSL",
        "sasl.mechanisms": "PLAIN",
        "sasl.username": os.environ["KAFKA_API_KEY"],
        "sasl.password": os.environ["KAFKA_API_SECRET"],
        "group.id": "nexaflow-fte-consumer",
        "auto.offset.reset": "earliest",
        "enable.auto.commit": True,
    }


API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")


def _handle_message(data: dict) -> None:
    ticket_id = data.get("ticket_id")
    if not ticket_id:
        print("[kafka_consumer] message missing ticket_id, skipping", file=sys.stderr)
        return
    try:
        r = httpx.post(
            f"{API_BASE_URL}/agent/process/{ticket_id}",
            timeout=30,
        )
        print(
            f"[kafka_consumer] processed {ticket_id}: {r.status_code}",
            file=sys.stderr,
        )
    except Exception as e:
        print(f"[kafka_consumer] HTTP error for {ticket_id}: {e}", file=sys.stderr)


def run_consumer() -> None:
    """Block forever, consuming from fte.tickets.incoming."""
    consumer = Consumer(get_consumer_config())
    consumer.subscribe(["fte.tickets.incoming"])
    print(
        "[kafka_consumer] started, listening on fte.tickets.incoming",
        file=sys.stderr,
    )
    try:
        while True:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                print(f"[kafka_consumer] error: {msg.error()}", file=sys.stderr)
                continue
            try:
                data = json.loads(msg.value().decode("utf-8"))
                _handle_message(data)
            except Exception as e:
                print(f"[kafka_consumer] processing error: {e}", file=sys.stderr)
                continue  # never crash consumer
    finally:
        consumer.close()
        print("[kafka_consumer] closed", file=sys.stderr)


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    run_consumer()
