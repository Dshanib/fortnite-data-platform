"""Reusable Kafka producer wrapper."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from kafka import KafkaProducer
from kafka.errors import KafkaError

from common.exceptions import KafkaProducerError
from common.logging import get_logger
from config.settings import Settings, get_settings

logger = get_logger(__name__)


class FortniteKafkaProducer:
    """JSON Kafka producer with structured logging."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or get_settings()
        self._producer: Optional[KafkaProducer] = None

    def _get_producer(self) -> KafkaProducer:
        if self._producer is None:
            self._producer = KafkaProducer(
                bootstrap_servers=self._settings.kafka_bootstrap_servers.split(","),
                value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                retries=3,
                acks="all",
            )
        return self._producer

    def send_event(
        self,
        topic: str,
        event: Dict[str, Any],
        *,
        key: Optional[str] = None,
    ) -> None:
        """Publish a JSON-serializable event to Kafka."""
        try:
            future = self._get_producer().send(topic, value=event, key=key)
            future.get(timeout=30)
            logger.info("Published event to topic=%s key=%s", topic, key)
        except KafkaError as exc:
            logger.error("Kafka publish failed topic=%s: %s", topic, exc)
            raise KafkaProducerError(f"Failed to publish to {topic}") from exc

    def flush(self) -> None:
        """Flush pending producer messages."""
        if self._producer is not None:
            self._producer.flush()

    def close(self) -> None:
        """Close the underlying producer."""
        if self._producer is not None:
            self._producer.close()
            self._producer = None
