"""Shop snapshot ingestion from Fortnite-API.com."""

from __future__ import annotations

import sys
from typing import Optional

from common.exceptions import ApiClientError, IngestionError, KafkaProducerError, ValidationError
from common.logging import configure_logging, get_logger
from config.settings import Settings, get_settings
from ingestion.clients.fortnite_api_client import FortniteApiClient
from ingestion.pipeline import IngestionPipeline

logger = get_logger(__name__)

SOURCE = "fortnite_api_com"
ENTITY = "shop"
ENDPOINT = "/v2/shop"


def run_ingestion(settings: Optional[Settings] = None) -> int:
    """Fetch /v2/shop and publish to fortnite.raw.shop."""
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    topic = settings.kafka_topic_shop
    pipeline = IngestionPipeline(settings)
    client = FortniteApiClient(settings)

    try:
        fetch = client.fetch_shop()
        pipeline.run_publish(
            source_name=SOURCE,
            entity=ENTITY,
            endpoint=ENDPOINT,
            topic=topic,
            fetch=fetch,
            message="Shop ingestion published to Kafka",
        )
        return 0
    except (IngestionError, ValidationError, ApiClientError, KafkaProducerError) as exc:
        logger.error("Shop ingestion failed: %s", exc)
        pipeline.emit_failure(
            source_name=SOURCE,
            entity=ENTITY,
            endpoint=ENDPOINT,
            topic=topic,
            exc=exc,
        )
        return 1
    finally:
        pipeline.finish()


if __name__ == "__main__":
    sys.exit(run_ingestion())
