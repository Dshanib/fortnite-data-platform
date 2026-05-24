"""Island engagement metrics ingestion from Fortnite Ecosystem API."""

from __future__ import annotations

import sys
import time
from typing import Any, Dict, List, Optional

from common.exceptions import ApiClientError, IngestionError, KafkaProducerError, ValidationError
from common.logging import configure_logging, get_logger
from common.models import SourceHealthEvent
from config.settings import Settings, get_settings
from ingestion.clients.ecosystem_api_client import EcosystemApiClient
from ingestion.island_catalog import iter_island_catalog_pages
from ingestion.pipeline import IngestionPipeline, build_envelope, print_ingestion_summary

logger = get_logger(__name__)

SOURCE = "fortnite_ecosystem_api"
ENTITY = "island_metrics"


def _island_code(island: Dict[str, Any]) -> str:
    return str(island.get("code") or island.get("displayName") or "")


def _metrics_endpoint(island_code: str, interval: str) -> str:
    return f"/islands/{island_code}/metrics/{interval}"


def _resolve_island_codes(
    client: EcosystemApiClient,
    settings: Settings,
    *,
    island_code: Optional[str],
    max_islands: Optional[int],
) -> List[str]:
    if island_code:
        return [island_code]

    demo = settings.fortnite_ecosystem_demo_island_code.strip()
    if demo:
        return [demo]

    if max_islands is None:
        max_islands = settings.fortnite_max_islands

    page_cap = settings.fortnite_ecosystem_max_island_pages
    summaries: List[Dict[str, Any]] = []
    for _, _, islands in iter_island_catalog_pages(
        client,
        page_size=settings.fortnite_ecosystem_island_page_size,
        max_pages=page_cap,
    ):
        summaries.extend(islands)

    codes = [code for island in summaries if (code := _island_code(island))]
    if not codes:
        raise IngestionError("No islands available for metrics ingestion")

    if max_islands is not None and max_islands > 0:
        logger.info(
            "Limiting island metrics to %s of %s islands (FORTNITE_MAX_ISLANDS)",
            max_islands,
            len(codes),
        )
        return codes[:max_islands]
    return codes


def run_ingestion(
    settings: Optional[Settings] = None,
    *,
    island_code: Optional[str] = None,
    max_islands: Optional[int] = None,
) -> int:
    """Fetch island metrics and publish to fortnite.raw.island_metrics."""
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    topic = settings.kafka_topic_island_metrics
    interval = settings.fortnite_ecosystem_metric_interval
    pipeline = IngestionPipeline(settings)
    client = EcosystemApiClient(settings)

    try:
        client.authenticate()
        codes = _resolve_island_codes(
            client, settings, island_code=island_code, max_islands=max_islands
        )

        delay = max(0.0, settings.fortnite_ecosystem_metrics_delay_seconds)
        for index, code in enumerate(codes):
            if index > 0 and delay > 0:
                time.sleep(delay)
            fetch = client.fetch_metrics_bundle(code, interval=interval)
            envelope = build_envelope(
                event_id=f"{pipeline.correlation_id}:{code}",
                source_name=SOURCE,
                event_type=ENTITY,
                fetch=fetch,
            )
            pipeline.publish_envelope(
                envelope,
                topic=topic,
                key=f"{pipeline.correlation_id}:{code}",
            )
            logger.info("Published island metrics island=%s", code)

        endpoint = _metrics_endpoint(codes[0], interval)
        pipeline.publish_health(
            SourceHealthEvent(
                source=SOURCE,
                entity=ENTITY,
                status="success",
                message=f"Island metrics published count={len(codes)}",
                endpoint=endpoint,
                topic=topic,
                http_status=200,
                record_count=len(codes),
                correlation_id=pipeline.correlation_id,
                kafka_publish="success",
            )
        )
        print_ingestion_summary(
            source=SOURCE,
            endpoint=endpoint,
            topic=topic,
            http_status=200,
            record_count=len(codes),
            kafka_publish="success",
            status="success",
        )
        return 0
    except (IngestionError, ValidationError, ApiClientError, KafkaProducerError) as exc:
        logger.error("Island metrics ingestion failed: %s", exc)
        sample_code = island_code or settings.fortnite_ecosystem_demo_island_code or "{code}"
        pipeline.emit_failure(
            source_name=SOURCE,
            entity=ENTITY,
            endpoint=_metrics_endpoint(sample_code, interval),
            topic=topic,
            exc=exc,
        )
        return 1
    finally:
        pipeline.finish()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ingest island metrics to Kafka.")
    parser.add_argument(
        "--max-islands",
        type=int,
        default=None,
        help="Limit number of islands (default: all; use FORTNITE_MAX_ISLANDS=0 for unlimited)",
    )
    parser.add_argument("--island-code", default=None, help="Single island code")
    cli = parser.parse_args()
    sys.exit(
        run_ingestion(
            island_code=cli.island_code,
            max_islands=cli.max_islands,
        )
    )
