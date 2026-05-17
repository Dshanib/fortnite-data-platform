"""Island catalog ingestion from Fortnite Ecosystem API."""

from __future__ import annotations

from typing import Optional

from common.exceptions import IngestionError, ValidationError
from common.logging import configure_logging, get_logger
from common.models import (
    IngestionMetadata,
    IslandsPayload,
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


def run_ingestion(settings: Optional[Settings] = None) -> None:
    """Fetch GET /islands and publish to fortnite.raw.islands."""
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    correlation_id = new_correlation_id()
    producer = FortniteKafkaProducer(settings)
    client = EcosystemApiClient(settings)

    try:
        client.authenticate()
        islands = client.list_island_summaries()
        captured_at = utc_now_iso()
        validate_timestamp(captured_at)
        metadata = IngestionMetadata(
            source=SOURCE,
            entity="islands",
            ingested_at=captured_at,
            correlation_id=correlation_id,
        )
        validate_metadata(metadata.to_dict())
        payload = IslandsPayload(islands=islands, captured_at=captured_at)
        event = RawEvent(metadata=metadata, payload=payload.to_dict())
        producer.send_event(
            settings.kafka_topic_islands, event.to_dict(), key=correlation_id
        )
        health = SourceHealthEvent(
            source=SOURCE,
            entity="islands",
            status="success",
            message=f"Islands ingested count={len(islands)}",
        )
        producer.send_event(
            settings.kafka_topic_ingestion_status,
            health.to_dict(),
            key=correlation_id,
        )
        logger.info("Islands ingestion complete count=%s", len(islands))
    except (IngestionError, ValidationError) as exc:
        logger.error("Islands ingestion failed: %s", exc)
        producer.send_event(
            settings.kafka_topic_ingestion_status,
            SourceHealthEvent(
                source=SOURCE, entity="islands", status="failed", message=str(exc)
            ).to_dict(),
            key=correlation_id,
        )
        raise
    finally:
        producer.flush()
        producer.close()


if __name__ == "__main__":
    run_ingestion()
