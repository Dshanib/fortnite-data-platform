"""Kafka producer configuration tests (mocked, no live broker)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from common.exceptions import KafkaProducerError
from producers.kafka_producer import FortniteKafkaProducer


@patch("producers.kafka_producer.KafkaProducer")
def test_send_event_uses_configured_bootstrap(mock_producer_cls) -> None:
    mock_producer = MagicMock()
    mock_future = MagicMock()
    mock_producer.send.return_value = mock_future
    mock_producer_cls.return_value = mock_producer

    producer = FortniteKafkaProducer()
    producer.send_event("fortnite.ops.ingestion_status", {"status": "success"}, key="k1")

    mock_producer_cls.assert_called_once()
    _, kwargs = mock_producer_cls.call_args
    assert kwargs["bootstrap_servers"] == ["localhost:9092"]
    mock_producer.send.assert_called_once()
    mock_future.get.assert_called_once()


@patch("producers.kafka_producer.KafkaProducer")
def test_send_event_requires_topic(mock_producer_cls) -> None:
    producer = FortniteKafkaProducer()
    with pytest.raises(KafkaProducerError):
        producer.send_event("", {"status": "success"})


def test_bootstrap_servers_from_settings() -> None:
    producer = FortniteKafkaProducer()
    assert producer.bootstrap_servers == ["localhost:9092"]
