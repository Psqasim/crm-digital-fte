"""
production/kafka/setup_topics.py
Phase 4E: Create required Kafka topics on Confluent Cloud via AdminClient.

Topics created:
  - fte.tickets.incoming   (primary inbound channel)
  - fte.tickets.processed  (post-agent processing)
  - fte.escalations        (human escalation events)
  - fte.metrics            (operational metrics)

Usage:
    python -m production.kafka.setup_topics
"""

from __future__ import annotations

import os
import sys

from confluent_kafka.admin import AdminClient, NewTopic


TOPICS: list[tuple[str, int, int]] = [
    # (name, num_partitions, replication_factor)
    ("fte.tickets.incoming", 3, 3),
    ("fte.tickets.processed", 3, 3),
    ("fte.escalations", 1, 3),
    ("fte.metrics", 1, 3),
]


def _get_admin_config() -> dict:
    return {
        "bootstrap.servers": os.environ["KAFKA_BOOTSTRAP_SERVERS"],
        "security.protocol": "SASL_SSL",
        "sasl.mechanisms": "PLAIN",
        "sasl.username": os.environ["KAFKA_API_KEY"],
        "sasl.password": os.environ["KAFKA_API_SECRET"],
    }


def create_topics() -> None:
    admin = AdminClient(_get_admin_config())

    new_topics = [
        NewTopic(name, num_partitions=parts, replication_factor=rf)
        for name, parts, rf in TOPICS
    ]

    results = admin.create_topics(new_topics)
    for topic, future in results.items():
        try:
            future.result()
            print(f"[kafka_admin] created topic: {topic}", file=sys.stderr)
        except Exception as e:
            # Topic already exists or other non-fatal error
            print(f"[kafka_admin] topic '{topic}': {e}", file=sys.stderr)


def list_topics() -> None:
    admin = AdminClient(_get_admin_config())
    metadata = admin.list_topics(timeout=10)
    print("[kafka_admin] topics on cluster:", file=sys.stderr)
    for name in sorted(metadata.topics):
        print(f"  - {name}", file=sys.stderr)


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    create_topics()
    list_topics()
