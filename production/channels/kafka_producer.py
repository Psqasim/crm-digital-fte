"""
production/channels/kafka_producer.py
Phase 4C: Shared async Kafka producer for Gmail and WhatsApp channel handlers.

Implements a lazy singleton AIOKafkaProducer that publishes TicketMessage
objects to the 'fte.tickets.incoming' topic.
"""

from __future__ import annotations

import dataclasses
import json
import os
import sys
from typing import TYPE_CHECKING

from aiokafka import AIOKafkaProducer

if TYPE_CHECKING:
    pass

__all__ = ["get_kafka_producer", "publish_ticket", "stop_kafka_producer"]

# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_producer: AIOKafkaProducer | None = None


# ---------------------------------------------------------------------------
# Lazy singleton accessor
# ---------------------------------------------------------------------------

async def get_kafka_producer() -> AIOKafkaProducer:
    """Return the shared AIOKafkaProducer, creating and starting it on first call."""
    global _producer
    if _producer is None:
        bootstrap_servers = os.environ.get("KAFKA_BOOTSTRAP_SERVERS")
        if not bootstrap_servers:
            raise EnvironmentError("KAFKA_BOOTSTRAP_SERVERS env var is required")
        _producer = AIOKafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode(),
        )
        await _producer.start()
    return _producer


# ---------------------------------------------------------------------------
# Publish helper
# ---------------------------------------------------------------------------

async def publish_ticket(message: object) -> None:
    """Serialize and publish a TicketMessage to 'fte.tickets.incoming'.

    Accepts any object that supports dataclasses.asdict() (TicketMessage is a
    dataclass) or has a model_dump() method (Pydantic models).
    """
    producer = await get_kafka_producer()

    # Serialise: prefer dataclass → dict, fall back to model_dump, then vars
    if dataclasses.is_dataclass(message) and not isinstance(message, type):
        payload = dataclasses.asdict(message)
    elif hasattr(message, "model_dump"):
        payload = message.model_dump()
    else:
        payload = vars(message)

    await producer.send_and_wait("fte.tickets.incoming", value=payload)
    print(f"[kafka] published {payload.get('channel', '?')} ticket {payload.get('id', '?')}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Shutdown helper
# ---------------------------------------------------------------------------

async def stop_kafka_producer() -> None:
    """Stop the singleton producer and reset it.  Idempotent — safe to call twice."""
    global _producer
    if _producer is not None:
        try:
            await _producer.stop()
        except Exception as e:
            print(f"[kafka] error stopping producer: {e}", file=sys.stderr)
        finally:
            _producer = None
