"""CCU ingestion pipeline."""

from __future__ import annotations

from typing import List, Optional

from common.exceptions import IngestionError, ValidationError
from common.logging import configure_logging, get_logger
from common.models import CcuPayload, IngestionMetadata, RawEvent, SourceHealthEvent, utc_now_iso
from common.utils import new_correlation_id
from common.validators import validate_ccu, validate_metadata
from config.settings import Settings, get_settings
from ingestion.clients.api_client import ApiClient
from ingestion.clients.scrape_client import ScrapeClient
from producers.kafka_producer import FortniteKafkaProducer

logger = get_logger(__name__)

# Configurable selectors; override via env-specific scrape targets later.
DEFAULT_CCU_SELECTORS: List[str] = [
    "[data-player-count]",
    ".player-count",
    "#player-count",
]


def fetch_ccu(
    settings: Settings,
    api_client: ApiClient,
    scrape_client: ScrapeClient,
) -> int:
    """Fetch CCU from API when key present, otherwise scrape configured URL."""
    if settings.fortnite_api_key:
        url = f"{settings.fortnite_api_base_url.rstrip('/')}/v2/stats/br/v2"
        data = api_client.get(
            url,
            headers={"Authorization": settings.fortnite_api_key},
        )
        count = data.get("data", {}).get("account", {}).get("stats", {}).get(
            "all", {}
        ).get("overall", {}).get("score")
        if count is None:
            count = data.get("data", {}).get("playersOnline")
        if count is not None:
            return validate_ccu(int(count))

    html = scrape_client.fetch_html(settings.ccu_source_url)
    scraped = scrape_client.extract_first_integer(html, DEFAULT_CCU_SELECTORS)
    if scraped is None:
        raise IngestionError("Could not extract CCU from configured source")
    return validate_ccu(scraped)


def run_ingestion(settings: Optional[Settings] = None) -> None:
    """Execute CCU ingestion and publish to Kafka."""
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    correlation_id = new_correlation_id()
    producer = FortniteKafkaProducer(settings)
    api_client = ApiClient(settings)
    scrape_client = ScrapeClient(settings)

    try:
        player_count = fetch_ccu(settings, api_client, scrape_client)
        captured_at = utc_now_iso()
        metadata = IngestionMetadata(
            source="ccu",
            entity="ccu",
            ingested_at=captured_at,
            correlation_id=correlation_id,
        )
        validate_metadata(metadata.to_dict())
        payload = CcuPayload(
            player_count=player_count,
            captured_at=captured_at,
            source_url=settings.ccu_source_url,
        )
        event = RawEvent(metadata=metadata, payload=payload.to_dict())
        producer.send_event(settings.kafka_topic_ccu, event.to_dict(), key=correlation_id)
        health = SourceHealthEvent(
            source="ccu",
            entity="ccu",
            status="success",
            message="CCU ingested",
        )
        producer.send_event(
            settings.kafka_topic_ingestion_status,
            health.to_dict(),
            key=correlation_id,
        )
        logger.info("CCU ingestion complete count=%s", player_count)
    except (IngestionError, ValidationError) as exc:
        logger.error("CCU ingestion failed: %s", exc)
        health = SourceHealthEvent(
            source="ccu",
            entity="ccu",
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
