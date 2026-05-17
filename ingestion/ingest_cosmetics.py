"""Cosmetics catalog ingestion pipeline."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from common.exceptions import IngestionError, ValidationError
from common.logging import configure_logging, get_logger
from common.models import (
    CosmeticsPayload,
    IngestionMetadata,
    RawEvent,
    SourceHealthEvent,
    utc_now_iso,
)
from common.utils import new_correlation_id
from common.validators import validate_metadata, validate_timestamp
from config.settings import Settings, get_settings
from ingestion.clients.api_client import ApiClient
from producers.kafka_producer import FortniteKafkaProducer

logger = get_logger(__name__)


def fetch_cosmetics(api_client: ApiClient, settings: Settings) -> List[Dict[str, Any]]:
    """Fetch cosmetics catalog from Fortnite API."""
    url = f"{settings.fortnite_api_base_url.rstrip('/')}/v2/cosmetics/br"
    headers = {}
    if settings.fortnite_api_key:
        headers["Authorization"] = settings.fortnite_api_key
    data = api_client.get(url, headers=headers or None)
    cosmetics = data.get("data") or []
    if not cosmetics:
        raise IngestionError("Cosmetics response was empty")
    if isinstance(cosmetics, dict):
        cosmetics = list(cosmetics.values())
    return cosmetics[:500]


def run_ingestion(settings: Optional[Settings] = None) -> None:
    """Execute cosmetics ingestion and publish to Kafka."""
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    correlation_id = new_correlation_id()
    producer = FortniteKafkaProducer(settings)
    api_client = ApiClient(settings)

    try:
        cosmetics = fetch_cosmetics(api_client, settings)
        captured_at = utc_now_iso()
        validate_timestamp(captured_at)
        metadata = IngestionMetadata(
            source="fortnite_api",
            entity="cosmetics",
            ingested_at=captured_at,
            correlation_id=correlation_id,
        )
        validate_metadata(metadata.to_dict())
        payload = CosmeticsPayload(cosmetics=cosmetics, captured_at=captured_at)
        event = RawEvent(metadata=metadata, payload=payload.to_dict())
        producer.send_event(
            settings.kafka_topic_cosmetics, event.to_dict(), key=correlation_id
        )
        health = SourceHealthEvent(
            source="fortnite_api",
            entity="cosmetics",
            status="success",
            message=f"Cosmetics ingested count={len(cosmetics)}",
        )
        producer.send_event(
            settings.kafka_topic_ingestion_status,
            health.to_dict(),
            key=correlation_id,
        )
        logger.info("Cosmetics ingestion complete count=%s", len(cosmetics))
    except (IngestionError, ValidationError) as exc:
        logger.error("Cosmetics ingestion failed: %s", exc)
        health = SourceHealthEvent(
            source="fortnite_api",
            entity="cosmetics",
            status="failed",
            message=str(exc),
        )
        producer.send_event(
            settings.kafka_topic_ingestion_status,
            health.to_dict(),
            key=correlation_id,
        )
        raise
    finally:
        producer.flush()
        producer.close()


if __name__ == "__main__":
    run_ingestion()
