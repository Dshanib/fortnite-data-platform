"""Item shop ingestion pipeline."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from common.exceptions import IngestionError, ValidationError
from common.logging import configure_logging, get_logger
from common.models import IngestionMetadata, RawEvent, ShopPayload, SourceHealthEvent, utc_now_iso
from common.utils import new_correlation_id
from common.validators import validate_metadata, validate_timestamp
from config.settings import Settings, get_settings
from ingestion.clients.api_client import ApiClient
from producers.kafka_producer import FortniteKafkaProducer

logger = get_logger(__name__)


def fetch_shop(api_client: ApiClient, settings: Settings) -> List[Dict[str, Any]]:
    """Fetch current shop from Fortnite API."""
    url = f"{settings.fortnite_api_base_url.rstrip('/')}/v2/shop/br"
    headers = {}
    if settings.fortnite_api_key:
        headers["Authorization"] = settings.fortnite_api_key
    data = api_client.get(url, headers=headers or None)
    entries = data.get("data", {}).get("entries") or data.get("data", {}).get("featured", [])
    if not entries:
        raise IngestionError("Shop response contained no items")
    return entries


def run_ingestion(settings: Optional[Settings] = None) -> None:
    """Execute shop ingestion and publish to Kafka."""
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    correlation_id = new_correlation_id()
    producer = FortniteKafkaProducer(settings)
    api_client = ApiClient(settings)

    try:
        items = fetch_shop(api_client, settings)
        captured_at = utc_now_iso()
        validate_timestamp(captured_at)
        metadata = IngestionMetadata(
            source="fortnite_api",
            entity="shop",
            ingested_at=captured_at,
            correlation_id=correlation_id,
        )
        validate_metadata(metadata.to_dict())
        payload = ShopPayload(items=items, captured_at=captured_at)
        event = RawEvent(metadata=metadata, payload=payload.to_dict())
        producer.send_event(settings.kafka_topic_shop, event.to_dict(), key=correlation_id)
        health = SourceHealthEvent(
            source="fortnite_api",
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
        health = SourceHealthEvent(
            source="fortnite_api",
            entity="shop",
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
