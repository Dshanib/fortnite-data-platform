"""Island engagement metrics ingestion from Fortnite Ecosystem API."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from common.exceptions import ApiClientError, IngestionError, ValidationError
from common.logging import configure_logging, get_logger
from common.models import (
    IngestionMetadata,
    IslandMetricsPayload,
    RawEvent,
    SourceHealthEvent,
    utc_now_iso,
)
from common.utils import new_correlation_id
from common.validators import validate_metadata, validate_timestamp
from config.settings import Settings, get_settings
from ingestion.clients.ecosystem_api_client import EcosystemApiClient
from producers.kafka_producer import FortniteKafkaProducer

logger = get_logger(__name__)
SOURCE = "fortnite_ecosystem_api"


def _island_code(island: Dict[str, Any]) -> str:
    return str(island.get("code") or island.get("displayName") or "")


def run_ingestion(settings: Optional[Settings] = None) -> None:
    """Fetch metrics per island and publish to fortnite.raw.island_metrics."""
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    correlation_id = new_correlation_id()
    producer = FortniteKafkaProducer(settings)
    client = EcosystemApiClient(settings)
    interval = settings.fortnite_ecosystem_metric_interval
    ingested = 0
    failures = 0

    try:
        client.authenticate()
        islands = client.list_island_summaries()
        captured_at = utc_now_iso()
        validate_timestamp(captured_at)

        for island in islands:
            code = _island_code(island)
            if not code:
                continue
            try:
                metrics = client.get_metrics_bundle(code, interval=interval)
            except ApiClientError as exc:
                failures += 1
                logger.warning("Metrics failed island=%s: %s", code, exc)
                if exc.status_code in {401, 403, 429}:
                    raise
                continue

            metadata = IngestionMetadata(
                source=SOURCE,
                entity="island_metrics",
                ingested_at=captured_at,
                correlation_id=correlation_id,
            )
            validate_metadata(metadata.to_dict())
            payload = IslandMetricsPayload(
                island_code=code,
                interval=interval,
                metrics=metrics,
                captured_at=captured_at,
            )
            event = RawEvent(metadata=metadata, payload=payload.to_dict())
            producer.send_event(
                settings.kafka_topic_island_metrics,
                event.to_dict(),
                key=f"{correlation_id}:{code}",
            )
            ingested += 1

        if ingested == 0:
            raise IngestionError("No island metrics ingested")

        health = SourceHealthEvent(
            source=SOURCE,
            entity="island_metrics",
            status="success",
            message=f"Metrics ingested islands={ingested} failures={failures}",
        )
        producer.send_event(
            settings.kafka_topic_ingestion_status,
            health.to_dict(),
            key=correlation_id,
        )
        logger.info(
            "Island metrics ingestion complete ingested=%s failures=%s",
            ingested,
            failures,
        )
    except (IngestionError, ValidationError, ApiClientError) as exc:
        logger.error("Island metrics ingestion failed: %s", exc)
        producer.send_event(
            settings.kafka_topic_ingestion_status,
            SourceHealthEvent(
                source=SOURCE,
                entity="island_metrics",
                status="failed",
                message=str(exc),
            ).to_dict(),
            key=correlation_id,
        )
        raise
    finally:
        producer.flush()
        producer.close()


if __name__ == "__main__":
    run_ingestion()
