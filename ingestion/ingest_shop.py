"""Shop snapshot ingestion from Fortnite-API.com."""

from __future__ import annotations

from typing import Optional

from common.exceptions import IngestionError, ValidationError
from common.logging import configure_logging, get_logger
from common.models import IngestionMetadata, RawEvent, ShopPayload, SourceHealthEvent, utc_now_iso
from common.utils import new_correlation_id
from common.validators import validate_metadata, validate_timestamp
from config.settings import Settings, get_settings
from ingestion.clients.fortnite_api_client import FortniteApiClient
from producers.kafka_producer import FortniteKafkaProducer

logger = get_logger(__name__)
SOURCE = "fortnite_api_com"


def run_ingestion(settings: Optional[Settings] = None) -> None:
    """Fetch /v2/shop and publish to fortnite.raw.shop."""
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    correlation_id = new_correlation_id()
    producer = FortniteKafkaProducer(settings)
    client = FortniteApiClient(settings)

    try:
        items = client.get_shop_entries()
        captured_at = utc_now_iso()
        validate_timestamp(captured_at)
        metadata = IngestionMetadata(
            source=SOURCE,
            entity="shop",
            ingested_at=captured_at,
            correlation_id=correlation_id,
        )
        validate_metadata(metadata.to_dict())
        payload = ShopPayload(items=items, captured_at=captured_at)
        event = RawEvent(metadata=metadata, payload=payload.to_dict())
        producer.send_event(settings.kafka_topic_shop, event.to_dict(), key=correlation_id)
        health = SourceHealthEvent(
            source=SOURCE,
            entity="shop",
            status="success",
            message=f"Shop ingested items={len(items)}",
        )
        producer.send_event(
            settings.kafka_topic_ingestion_status,
            health.to_dict(),
            key=correlation_id,
        )
        logger.info("Shop ingestion complete items=%s", len(items))
    except (IngestionError, ValidationError) as exc:
        logger.error("Shop ingestion failed: %s", exc)
        producer.send_event(
            settings.kafka_topic_ingestion_status,
            SourceHealthEvent(
                source=SOURCE, entity="shop", status="failed", message=str(exc)
            ).to_dict(),
            key=correlation_id,
        )
        raise
    finally:
        producer.flush()
        producer.close()


if __name__ == "__main__":
    run_ingestion()
