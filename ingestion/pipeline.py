"""Shared Kafka publishing helpers for API ingestion."""

from __future__ import annotations

import sys
from typing import Any, Dict, Iterator, Optional

from common.exceptions import ApiClientError, KafkaProducerError
from common.logging import get_logger
from common.models import IngestionEventEnvelope, SourceHealthEvent, utc_now_iso
from common.utils import new_correlation_id
from config.settings import Settings
from ingestion.clients.api_result import ApiFetchResult
from producers.kafka_producer import FortniteKafkaProducer

logger = get_logger(__name__)


def build_envelope(
    *,
    event_id: str,
    source_name: str,
    event_type: str,
    fetch: ApiFetchResult,
    ingested_at: Optional[str] = None,
) -> IngestionEventEnvelope:
    """Build the standard raw-event envelope from an API fetch."""
    return IngestionEventEnvelope(
        event_id=event_id,
        source_name=source_name,
        event_type=event_type,
        event_time=fetch.fetched_at,
        ingested_at=ingested_at or utc_now_iso(),
        request_status=fetch.request_status,
        latency_ms=round(fetch.latency_ms, 2),
        payload=fetch.body,
    )


def record_count(event_type: str, payload: Dict[str, Any]) -> Optional[int]:
    """Derive a record count from a raw API payload when possible."""
    data = payload.get("data")
    if event_type == "shop":
        if isinstance(data, dict):
            for key in ("entries", "featured", "daily"):
                entries = data.get(key)
                if isinstance(entries, list):
                    return len(entries)
            lists = [value for value in data.values() if isinstance(value, list) and value]
            return len(lists[0]) if lists else None
        return None
    if event_type in {"cosmetics", "islands"}:
        if isinstance(data, list):
            return len(data)
        if isinstance(data, dict):
            return len(data)
    if event_type == "island_metrics":
        return 1
    return None


def safe_print(message: str) -> None:
    """Print without failing on Windows console encoding."""
    try:
        print(message)
    except UnicodeEncodeError:
        encoding = sys.stdout.encoding or "utf-8"
        print(message.encode(encoding, errors="replace").decode(encoding, errors="replace"))


def print_ingestion_summary(
    *,
    source: str,
    endpoint: str,
    topic: str,
    http_status: Optional[int],
    record_count: Optional[int],
    kafka_publish: str,
    status: str,
    kafka_messages: Optional[int] = None,
) -> None:
    """Print a concise ingestion summary (no secrets)."""
    safe_print(f"\n{source}")
    safe_print(f"  endpoint: {endpoint}")
    safe_print(f"  topic: {topic}")
    safe_print(f"  http_status: {http_status if http_status is not None else 'n/a'}")
    if record_count is not None:
        safe_print(f"  record_count: {record_count}")
    if kafka_messages is not None:
        safe_print(f"  kafka_messages: {kafka_messages}")
    safe_print(f"  kafka_publish: {kafka_publish}")
    safe_print(f"  status: {status}")


class IngestionPipeline:
    """Publish ingestion envelopes and health events to Kafka."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._producer = FortniteKafkaProducer(settings)
        self._correlation_id = new_correlation_id()

    @property
    def correlation_id(self) -> str:
        return self._correlation_id

    def publish_envelope(
        self,
        envelope: IngestionEventEnvelope,
        *,
        topic: str,
        key: Optional[str] = None,
    ) -> None:
        self._producer.send_event(topic, envelope.to_dict(), key=key or envelope.event_id)

    def publish_health(
        self,
        health: SourceHealthEvent,
    ) -> None:
        self._producer.send_event(
            self._settings.kafka_topic_ingestion_status,
            health.to_dict(),
            key=health.correlation_id or self._correlation_id,
        )

    def finish(self) -> None:
        self._producer.flush()
        self._producer.close()

    def run_publish(
        self,
        *,
        source_name: str,
        entity: str,
        endpoint: str,
        topic: str,
        fetch: ApiFetchResult,
        message: str,
        record_count_value: Optional[int] = None,
    ) -> None:
        """Publish raw envelope and success health event; print summary."""
        envelope = build_envelope(
            event_id=self._correlation_id,
            source_name=source_name,
            event_type=entity,
            fetch=fetch,
        )
        count = record_count_value if record_count_value is not None else record_count(
            entity, fetch.body
        )
        try:
            self.publish_envelope(envelope, topic=topic)
            self.publish_health(
                SourceHealthEvent(
                    source=source_name,
                    entity=entity,
                    status="success",
                    message=message,
                    endpoint=endpoint,
                    topic=topic,
                    http_status=fetch.status_code,
                    record_count=count,
                    correlation_id=self._correlation_id,
                    kafka_publish="success",
                )
            )
            print_ingestion_summary(
                source=source_name,
                endpoint=endpoint,
                topic=topic,
                http_status=fetch.status_code,
                record_count=count,
                kafka_publish="success",
                status="success",
            )
        except KafkaProducerError as exc:
            self.emit_failure(
                source_name=source_name,
                entity=entity,
                endpoint=endpoint,
                topic=topic,
                exc=exc,
                http_status=fetch.status_code,
            )
            raise

    def run_publish_chunked(
        self,
        *,
        source_name: str,
        entity: str,
        endpoint: str,
        topic: str,
        fetch: ApiFetchResult,
        chunk_payloads: Iterator[Dict[str, Any]],
        message: str,
        total_record_count: int,
    ) -> int:
        """Publish multiple envelope chunks (same API fetch metadata)."""
        published = 0
        try:
            for batch_index, payload in enumerate(chunk_payloads):
                chunk_fetch = ApiFetchResult(
                    status_code=fetch.status_code,
                    latency_ms=fetch.latency_ms,
                    body=payload,
                    fetched_at=fetch.fetched_at,
                )
                envelope = build_envelope(
                    event_id=f"{self._correlation_id}:{batch_index}",
                    source_name=source_name,
                    event_type=entity,
                    fetch=chunk_fetch,
                )
                self.publish_envelope(
                    envelope,
                    topic=topic,
                    key=f"{self._correlation_id}:{batch_index}",
                )
                published += 1

            self.publish_health(
                SourceHealthEvent(
                    source=source_name,
                    entity=entity,
                    status="success",
                    message=f"{message} chunks={published}",
                    endpoint=endpoint,
                    topic=topic,
                    http_status=fetch.status_code,
                    record_count=total_record_count,
                    correlation_id=self._correlation_id,
                    kafka_publish="success",
                )
            )
            print_ingestion_summary(
                source=source_name,
                endpoint=endpoint,
                topic=topic,
                http_status=fetch.status_code,
                record_count=total_record_count,
                kafka_messages=published,
                kafka_publish="success",
                status="success",
            )
            return published
        except KafkaProducerError as exc:
            self.emit_failure(
                source_name=source_name,
                entity=entity,
                endpoint=endpoint,
                topic=topic,
                exc=exc,
                http_status=fetch.status_code,
            )
            raise

    def emit_failure(
        self,
        *,
        source_name: str,
        entity: str,
        endpoint: str,
        topic: str,
        exc: Exception,
        http_status: Optional[int] = None,
    ) -> None:
        """Publish failure health event and print summary."""
        status_code = http_status
        if status_code is None and isinstance(exc, ApiClientError):
            status_code = exc.status_code
        message = str(exc)
        kafka_publish = "skipped"
        try:
            self.publish_health(
                SourceHealthEvent(
                    source=source_name,
                    entity=entity,
                    status="failed",
                    message=message,
                    endpoint=endpoint,
                    topic=topic,
                    http_status=status_code,
                    correlation_id=self._correlation_id,
                    kafka_publish="success",
                )
            )
            kafka_publish = "success"
        except KafkaProducerError:
            kafka_publish = "failed"
            logger.error("Failed to publish ingestion health event entity=%s", entity)

        print_ingestion_summary(
            source=source_name,
            endpoint=endpoint,
            topic=topic,
            http_status=status_code,
            record_count=None,
            kafka_publish=kafka_publish,
            status="failed",
        )
