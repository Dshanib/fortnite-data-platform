"""Island catalog ingestion from Fortnite Ecosystem API."""

from __future__ import annotations

import sys
import time
from typing import Optional

from common.exceptions import ApiClientError, IngestionError, KafkaProducerError, ValidationError
from common.logging import configure_logging, get_logger
from config.settings import Settings, get_settings
from ingestion.clients.api_result import ApiFetchResult
from ingestion.clients.ecosystem_api_client import EcosystemApiClient
from ingestion.island_catalog import (
    build_island_page_payload,
    effective_page_cap,
    iter_island_catalog_pages,
)
from ingestion.pipeline import IngestionPipeline, build_envelope

logger = get_logger(__name__)

SOURCE = "fortnite_ecosystem_api"
ENTITY = "islands"
ENDPOINT = "/islands"


def run_ingestion(settings: Optional[Settings] = None) -> int:
    """Fetch GET /islands pages and publish each page to fortnite.raw.islands."""
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    topic = settings.kafka_topic_islands
    pipeline = IngestionPipeline(settings)
    client = EcosystemApiClient(settings)

    try:
        client.authenticate()
        page_size = settings.fortnite_ecosystem_island_page_size
        max_pages = effective_page_cap(settings.fortnite_ecosystem_catalog_max_pages)
        delay = max(0.0, settings.fortnite_ecosystem_catalog_page_delay_seconds)

        published = 0
        total_records = 0
        first_fetch: Optional[ApiFetchResult] = None

        for page_index, fetch, islands in iter_island_catalog_pages(
            client, page_size=page_size, max_pages=max_pages
        ):
            if not islands:
                continue
            if first_fetch is None:
                first_fetch = fetch

            payload = build_island_page_payload(
                page_index=page_index,
                islands=islands,
                correlation_id=pipeline.correlation_id,
            )
            chunk_fetch = ApiFetchResult(
                status_code=fetch.status_code,
                latency_ms=fetch.latency_ms,
                body=payload,
                fetched_at=fetch.fetched_at,
            )
            envelope = build_envelope(
                event_id=f"{pipeline.correlation_id}:{page_index}",
                source_name=SOURCE,
                event_type=ENTITY,
                fetch=chunk_fetch,
            )
            pipeline.publish_envelope(
                envelope,
                topic=topic,
                key=f"{pipeline.correlation_id}:{page_index}",
            )
            published += 1
            total_records += len(islands)
            logger.info(
                "Published islands page=%s size=%s total_so_far=%s",
                page_index,
                len(islands),
                total_records,
            )
            if delay > 0:
                time.sleep(delay)

        if published == 0 or first_fetch is None:
            raise IngestionError("Ecosystem API returned no islands")

        from common.models import SourceHealthEvent
        from ingestion.pipeline import print_ingestion_summary, record_count

        pipeline.publish_health(
            SourceHealthEvent(
                source=SOURCE,
                entity=ENTITY,
                status="success",
                message=(
                    f"Islands catalog pages={published} records={total_records} "
                    f"(max_pages={max_pages})"
                ),
                endpoint=ENDPOINT,
                topic=topic,
                http_status=first_fetch.status_code,
                record_count=total_records,
                correlation_id=pipeline.correlation_id,
                kafka_publish="success",
            )
        )
        print_ingestion_summary(
            source=SOURCE,
            endpoint=ENDPOINT,
            topic=topic,
            http_status=first_fetch.status_code,
            record_count=total_records,
            kafka_messages=published,
            kafka_publish="success",
            status="success",
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
