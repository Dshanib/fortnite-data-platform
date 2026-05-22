"""Reusable Kafka producer wrapper."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from kafka import KafkaProducer
from kafka.errors import KafkaError, NoBrokersAvailable

from common.exceptions import KafkaProducerError
from common.logging import get_logger
from config.settings import Settings, get_settings

logger = get_logger(__name__)


class FortniteKafkaProducer:
    """JSON Kafka producer with structured logging (no hardcoded topics or brokers)."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or get_settings()
        self._producer: Optional[KafkaProducer] = None

    @property
    def bootstrap_servers(self) -> List[str]:
        """Return configured Kafka bootstrap servers."""
        return [
            server.strip()
            for server in self._settings.kafka_bootstrap_servers.split(",")
            if server.strip()
        ]

    def _get_producer(self) -> KafkaProducer:
        if self._producer is None:
            self._producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda value: json.dumps(value, default=str).encode("utf-8"),
                key_serializer=lambda key: key.encode("utf-8") if key else None,
                retries=3,
                acks="all",
                request_timeout_ms=30_000,
                max_block_ms=30_000,
            )
        return self._producer

    def send_event(
        self,
        topic: str,
        event: Dict[str, Any],
        *,
        key: Optional[str] = None,
    ) -> None:
        """Publish a JSON-serializable event to the given topic."""
        if not topic or not topic.strip():
            raise KafkaProducerError("Kafka topic name is required")
        try:
            future = self._get_producer().send(topic, value=event, key=key)
            future.get(timeout=30)
            logger.info(
                "Published event bootstrap=%s topic=%s key=%s",
                self.bootstrap_servers,
                topic,
                key,
            )
        except NoBrokersAvailable as exc:
            logger.error("Kafka broker unavailable bootstrap=%s", self.bootstrap_servers)
            raise KafkaProducerError("Kafka broker unavailable") from exc
        except KafkaError as exc:
            logger.error("Kafka publish failed topic=%s: %s", topic, exc)
            raise KafkaProducerError(f"Failed to publish to {topic}") from exc

    def flush(self) -> None:
        """Flush pending producer messages."""
        if self._producer is not None:
            self._producer.flush()
            logger.debug("Kafka producer flushed")

    def close(self) -> None:
        """Close the underlying producer."""
        if self._producer is not None:
            self._producer.close()
            self._producer = None
            logger.debug("Kafka producer closed")
