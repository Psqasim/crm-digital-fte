"""
production/tests/test_kafka.py
Phase 4E: Tests for Kafka producer config, publish_ticket, and consumer parsing.
"""

from __future__ import annotations

import asyncio
import json
import os
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Producer config tests
# ---------------------------------------------------------------------------


class TestProducerConfig:
    """Producer config is built correctly from environment variables."""

    def test_config_contains_all_required_keys(self, monkeypatch):
        monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "pkc-test.confluent.cloud:9092")
        monkeypatch.setenv("KAFKA_API_KEY", "testkey")
        monkeypatch.setenv("KAFKA_API_SECRET", "testsecret")

        # Import after env vars are set
        import importlib
        import production.channels.kafka_producer as mod
        importlib.reload(mod)

        config = mod._get_producer_config()

        assert config["bootstrap.servers"] == "pkc-test.confluent.cloud:9092"
        assert config["security.protocol"] == "SASL_SSL"
        assert config["sasl.mechanisms"] == "PLAIN"
        assert config["sasl.username"] == "testkey"
        assert config["sasl.password"] == "testsecret"

    def test_config_uses_sasl_ssl_not_plaintext(self, monkeypatch):
        monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "broker:9092")
        monkeypatch.setenv("KAFKA_API_KEY", "k")
        monkeypatch.setenv("KAFKA_API_SECRET", "s")

        import importlib
        import production.channels.kafka_producer as mod
        importlib.reload(mod)

        config = mod._get_producer_config()
        assert config["security.protocol"] == "SASL_SSL"
        assert config["sasl.mechanisms"] == "PLAIN"


# ---------------------------------------------------------------------------
# publish_ticket graceful failure tests
# ---------------------------------------------------------------------------


class TestPublishTicket:
    """publish_ticket returns False gracefully when Kafka is unavailable."""

    def test_returns_false_when_producer_raises(self, monkeypatch):
        monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "bad-host:9092")
        monkeypatch.setenv("KAFKA_API_KEY", "k")
        monkeypatch.setenv("KAFKA_API_SECRET", "s")

        import importlib
        import production.channels.kafka_producer as mod
        importlib.reload(mod)

        with patch("production.channels.kafka_producer.Producer") as mock_producer_cls:
            mock_producer_cls.side_effect = Exception("Connection refused")
            result = asyncio.run(mod.publish_ticket({"ticket_id": "t-001"}))

        assert result is False

    def test_returns_false_when_flush_raises(self, monkeypatch):
        monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "broker:9092")
        monkeypatch.setenv("KAFKA_API_KEY", "k")
        monkeypatch.setenv("KAFKA_API_SECRET", "s")

        import importlib
        import production.channels.kafka_producer as mod
        importlib.reload(mod)

        mock_producer = MagicMock()
        mock_producer.flush.side_effect = Exception("Timeout")

        with patch("production.channels.kafka_producer.Producer", return_value=mock_producer):
            result = asyncio.run(mod.publish_ticket({"ticket_id": "t-002"}))

        assert result is False

    def test_returns_true_on_success(self, monkeypatch):
        monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "broker:9092")
        monkeypatch.setenv("KAFKA_API_KEY", "k")
        monkeypatch.setenv("KAFKA_API_SECRET", "s")

        import importlib
        import production.channels.kafka_producer as mod
        importlib.reload(mod)

        mock_producer = MagicMock()

        with patch("production.channels.kafka_producer.Producer", return_value=mock_producer):
            result = asyncio.run(mod.publish_ticket({"ticket_id": "t-003"}))

        assert result is True
        mock_producer.produce.assert_called_once()
        mock_producer.flush.assert_called_once_with(timeout=5)

    def test_produce_uses_ticket_id_as_key(self, monkeypatch):
        monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "broker:9092")
        monkeypatch.setenv("KAFKA_API_KEY", "k")
        monkeypatch.setenv("KAFKA_API_SECRET", "s")

        import importlib
        import production.channels.kafka_producer as mod
        importlib.reload(mod)

        mock_producer = MagicMock()
        with patch("production.channels.kafka_producer.Producer", return_value=mock_producer):
            asyncio.run(mod.publish_ticket({"ticket_id": "t-abc"}))

        call_kwargs = mock_producer.produce.call_args
        assert call_kwargs.kwargs["key"] == "t-abc"

    def test_produce_default_topic_is_incoming(self, monkeypatch):
        monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "broker:9092")
        monkeypatch.setenv("KAFKA_API_KEY", "k")
        monkeypatch.setenv("KAFKA_API_SECRET", "s")

        import importlib
        import production.channels.kafka_producer as mod
        importlib.reload(mod)

        mock_producer = MagicMock()
        with patch("production.channels.kafka_producer.Producer", return_value=mock_producer):
            asyncio.run(mod.publish_ticket({"ticket_id": "t-xyz"}))

        call_args = mock_producer.produce.call_args
        assert call_args.args[0] == "fte.tickets.incoming"


# ---------------------------------------------------------------------------
# Consumer message parsing tests
# ---------------------------------------------------------------------------


class TestConsumerMessageParsing:
    """Consumer correctly parses messages and calls agent endpoint."""

    def test_handle_message_calls_httpx_post(self, monkeypatch):
        """_handle_message makes a POST to /agent/process/<ticket_id>."""
        monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "broker:9092")
        monkeypatch.setenv("KAFKA_API_KEY", "k")
        monkeypatch.setenv("KAFKA_API_SECRET", "s")

        import importlib
        import production.kafka.consumer as mod
        importlib.reload(mod)

        with patch("production.kafka.consumer.httpx") as mock_httpx:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_httpx.post.return_value = mock_response

            mod._handle_message({"ticket_id": "t-111", "channel": "gmail"})

        mock_httpx.post.assert_called_once()
        call_url = mock_httpx.post.call_args.args[0]
        assert "t-111" in call_url
        assert "/agent/process/" in call_url

    def test_handle_message_skips_missing_ticket_id(self, monkeypatch):
        """_handle_message does nothing when ticket_id is absent."""
        monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "broker:9092")
        monkeypatch.setenv("KAFKA_API_KEY", "k")
        monkeypatch.setenv("KAFKA_API_SECRET", "s")

        import importlib
        import production.kafka.consumer as mod
        importlib.reload(mod)

        with patch("production.kafka.consumer.httpx") as mock_httpx:
            mod._handle_message({"channel": "whatsapp"})  # no ticket_id

        mock_httpx.post.assert_not_called()

    def test_handle_message_survives_httpx_error(self, monkeypatch):
        """_handle_message catches HTTP errors and does not raise."""
        monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "broker:9092")
        monkeypatch.setenv("KAFKA_API_KEY", "k")
        monkeypatch.setenv("KAFKA_API_SECRET", "s")

        import importlib
        import production.kafka.consumer as mod
        importlib.reload(mod)

        with patch("production.kafka.consumer.httpx") as mock_httpx:
            mock_httpx.post.side_effect = Exception("Connection refused")
            # Must not raise
            mod._handle_message({"ticket_id": "t-222"})

    def test_get_consumer_config_keys(self, monkeypatch):
        monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "pkc.confluent.cloud:9092")
        monkeypatch.setenv("KAFKA_API_KEY", "mykey")
        monkeypatch.setenv("KAFKA_API_SECRET", "mysecret")

        import importlib
        import production.kafka.consumer as mod
        importlib.reload(mod)

        config = mod.get_consumer_config()

        assert config["security.protocol"] == "SASL_SSL"
        assert config["sasl.mechanisms"] == "PLAIN"
        assert config["sasl.username"] == "mykey"
        assert config["sasl.password"] == "mysecret"
        assert config["group.id"] == "nexaflow-fte-consumer"
        assert config["auto.offset.reset"] == "earliest"


# ---------------------------------------------------------------------------
# delivery_report tests
# ---------------------------------------------------------------------------


class TestDeliveryReport:
    def test_delivery_report_on_error(self, capsys):
        import importlib
        import production.channels.kafka_producer as mod
        importlib.reload(mod)

        err = MagicMock()
        err.__str__ = lambda self: "Broker not available"
        mod.delivery_report(err, None)
        captured = capsys.readouterr()
        assert "delivery failed" in captured.err

    def test_delivery_report_on_success(self, capsys):
        import importlib
        import production.channels.kafka_producer as mod
        importlib.reload(mod)

        mock_msg = MagicMock()
        mock_msg.topic.return_value = "fte.tickets.incoming"
        mock_msg.partition.return_value = 0
        mod.delivery_report(None, mock_msg)
        captured = capsys.readouterr()
        assert "delivered to" in captured.err
