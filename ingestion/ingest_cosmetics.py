"""Cosmetics catalog ingestion from Fortnite-API.com."""

from __future__ import annotations

import sys
from typing import Optional

from common.exceptions import ApiClientError, IngestionError, KafkaProducerError, ValidationError
from common.logging import configure_logging, get_logger
from config.settings import Settings, get_settings
from ingestion.chunking import extract_cosmetics_records, iter_cosmetics_chunk_payloads
from ingestion.clients.fortnite_api_client import FortniteApiClient
from ingestion.pipeline import IngestionPipeline

logger = get_logger(__name__)

SOURCE = "fortnite_api_com"
ENTITY = "cosmetics"
ENDPOINT = "/v2/cosmetics/br"


def run_ingestion(settings: Optional[Settings] = None) -> int:
    """Fetch /v2/cosmetics/br and publish to fortnite.raw.cosmetics in chunks."""
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    topic = settings.kafka_topic_cosmetics
    pipeline = IngestionPipeline(settings)
    client = FortniteApiClient(settings)

    try:
        fetch = client.fetch_cosmetics()
        records = extract_cosmetics_records(fetch.body)
        chunk_size = settings.fortnite_cosmetics_kafka_chunk_size
        chunks = iter_cosmetics_chunk_payloads(
            fetch.body,
            chunk_size=chunk_size,
            correlation_id=pipeline.correlation_id,
        )
        pipeline.run_publish_chunked(
            source_name=SOURCE,
            entity=ENTITY,
            endpoint=ENDPOINT,
            topic=topic,
            fetch=fetch,
            chunk_payloads=chunks,
            message="Cosmetics ingestion published to Kafka",
            total_record_count=len(records),
        )
        return 0
    except (IngestionError, ValidationError, ApiClientError, KafkaProducerError) as exc:
        logger.error("Cosmetics ingestion failed: %s", exc)
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
