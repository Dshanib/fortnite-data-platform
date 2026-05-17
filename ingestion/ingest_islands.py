"""Island catalog ingestion from Fortnite Ecosystem API."""

from __future__ import annotations

import sys
from typing import Optional

from common.exceptions import ApiClientError, IngestionError, KafkaProducerError, ValidationError
from common.logging import configure_logging, get_logger
from config.settings import Settings, get_settings
from ingestion.clients.ecosystem_api_client import EcosystemApiClient
from ingestion.pipeline import IngestionPipeline

logger = get_logger(__name__)

SOURCE = "fortnite_ecosystem_api"
ENTITY = "islands"
ENDPOINT = "/islands"


def run_ingestion(settings: Optional[Settings] = None) -> int:
    """Fetch GET /islands and publish to fortnite.raw.islands."""
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    topic = settings.kafka_topic_islands
    pipeline = IngestionPipeline(settings)
    client = EcosystemApiClient(settings)

    try:
        client.authenticate()
        fetch = client.fetch_islands()
        if not fetch.body.get("data"):
            raise IngestionError("Ecosystem API returned no islands")
        pipeline.run_publish(
            source_name=SOURCE,
            entity=ENTITY,
            endpoint=ENDPOINT,
            topic=topic,
            fetch=fetch,
            message="Islands ingestion published to Kafka",
        )
        return 0
    except (IngestionError, ValidationError, ApiClientError, KafkaProducerError) as exc:
        logger.error("Islands ingestion failed: %s", exc)
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
