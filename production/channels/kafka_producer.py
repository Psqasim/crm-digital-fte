"""
production/channels/kafka_producer.py
Phase 4E: Confluent Cloud Kafka producer (replaces aiokafka singleton).

Publishes ticket dicts to 'fte.tickets.incoming' (or any specified topic).
Always best-effort — never raises; returns False on failure so callers can
fall back gracefully.
"""

from __future__ import annotations

import json
import os
import sys

from confluent_kafka import Producer


__all__ = ["publish_ticket", "delivery_report", "stop_kafka_producer"]


def _get_producer_config() -> dict:
    return {
        "bootstrap.servers": os.environ["KAFKA_BOOTSTRAP_SERVERS"],
        "security.protocol": "SASL_SSL",
        "sasl.mechanisms": "PLAIN",
        "sasl.username": os.environ["KAFKA_API_KEY"],
        "sasl.password": os.environ["KAFKA_API_SECRET"],
    }


def delivery_report(err, msg) -> None:  # noqa: ANN001
    if err:
        print(f"[kafka] delivery failed: {err}", file=sys.stderr)
    else:
        print(
            f"[kafka] delivered to {msg.topic()} [{msg.partition()}]",
            file=sys.stderr,
        )


async def stop_kafka_producer() -> None:
    """No-op — confluent-kafka Producer is stateless; kept for API compatibility."""


async def publish_ticket(
    message_dict: dict,
    topic: str = "fte.tickets.incoming",
) -> bool:
    """Publish *message_dict* to *topic*.

    Synchronous under the hood (confluent-kafka is not async-native); safe to
    await from async callers. Returns True on success, False on any error.
    """
    try:
        p = Producer(_get_producer_config())
        p.produce(
            topic,
            key=str(message_dict.get("ticket_id", "unknown")),
            value=json.dumps(message_dict),
            callback=delivery_report,
        )
        p.flush(timeout=5)
        return True
    except Exception as e:
        print(f"[kafka_error] publish failed: {e}", file=sys.stderr)
        return False  # best-effort — never raise
