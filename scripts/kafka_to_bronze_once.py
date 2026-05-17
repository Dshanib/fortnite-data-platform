#!/usr/bin/env python3
"""Consume Kafka topics once and persist raw events to MinIO bronze (JSON)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from kafka import KafkaConsumer
from kafka.errors import KafkaError, NoBrokersAvailable

from scripts._script_runtime import bootstrap, safe_print

bootstrap()

from common.exceptions import StorageError
from common.logging import configure_logging, get_logger
from config.settings import Settings, get_settings
from storage.healthcheck import ensure_minio_ready
from storage.paths import TOPIC_TO_BRONZE_SOURCE, bronze_topics
from storage.writers import write_raw_event_to_bronze

logger = get_logger(__name__)

DEFAULT_MAX_MESSAGES = 10


def _topic_map(settings: Settings) -> Dict[str, str]:
    return {
        settings.kafka_topic_shop: "shop",
        settings.kafka_topic_cosmetics: "cosmetics",
        settings.kafka_topic_islands: "islands",
        settings.kafka_topic_island_metrics: "island_metrics",
        settings.kafka_topic_ingestion_status: "ingestion_status",
    }


def _resolve_topics(
    settings: Settings,
    *,
    topic: Optional[str],
    full: bool,
) -> List[str]:
    if full:
        return list(bronze_topics())
    if topic:
        if topic not in TOPIC_TO_BRONZE_SOURCE:
            known = ", ".join(sorted(TOPIC_TO_BRONZE_SOURCE))
            raise StorageError(f"Unknown topic {topic!r}. Expected one of: {known}")
        return [topic]
    return [settings.kafka_topic_shop]


def _consume_topic(
    settings: Settings,
    topic: str,
    max_messages: int,
) -> List[dict]:
    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=settings.kafka_bootstrap_servers.split(","),
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        consumer_timeout_ms=5000,
        value_deserializer=lambda raw: __import__("json").loads(raw.decode("utf-8")),
    )
    messages: List[dict] = []
    try:
        for record in consumer:
            if not isinstance(record.value, dict):
                logger.warning("Skipping non-dict message topic=%s offset=%s", topic, record.offset)
                continue
            messages.append(record.value)
            if len(messages) >= max_messages:
                break
    finally:
        consumer.close()
    return messages


def run(
    settings: Settings,
    *,
    topics: List[str],
    max_messages: int,
) -> int:
    """Consume topics and write bronze objects; return exit code."""
    configure_logging(settings.log_level)
    safe_print(f"Kafka bootstrap: {settings.kafka_bootstrap_servers}")
    ensure_minio_ready(settings)
    safe_print(
        f"MinIO profile={settings.minio_profile} "
        f"endpoint={settings.minio_endpoint} bucket={settings.minio_bucket}"
    )

    total_failures = 0
    for topic in topics:
        consumed = 0
        written = 0
        failures = 0
        paths: List[str] = []

        try:
            events = _consume_topic(settings, topic, max_messages)
            consumed = len(events)
            for event in events:
                try:
                    key = write_raw_event_to_bronze(event, topic=topic, settings=settings)
                    written += 1
                    paths.append(key)
                except StorageError as exc:
                    failures += 1
                    logger.error("Bronze write failed topic=%s: %s", topic, exc)
            total_failures += failures
        except NoBrokersAvailable:
            safe_print(f"\n{topic}")
            safe_print("  kafka: connection failed (start zookeeper + kafka)")
            return 1
        except KafkaError as exc:
            safe_print(f"\n{topic}")
            safe_print(f"  kafka: error — {exc}")
            return 1

        safe_print(f"\n{topic}")
        safe_print(f"  messages_consumed: {consumed}")
        safe_print(f"  messages_written: {written}")
        safe_print(f"  failures: {failures}")
        for path in paths[:5]:
            safe_print(f"  path: s3://{settings.minio_bucket}/{path}")
        if len(paths) > 5:
            safe_print(f"  ... and {len(paths) - 5} more path(s)")

    safe_print(f"\nKafka → Bronze: {'SUCCESS' if total_failures == 0 else 'PARTIAL'}")
    return 1 if total_failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Consume Kafka messages once and write raw JSON to MinIO bronze.",
    )
    parser.add_argument(
        "--topic",
        help="Single Kafka topic (default: fortnite.raw.shop from settings)",
    )
    parser.add_argument(
        "--max-messages",
        type=int,
        default=DEFAULT_MAX_MESSAGES,
        help=f"Max messages per topic (default: {DEFAULT_MAX_MESSAGES})",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Process all configured raw/ops topics",
    )
    args = parser.parse_args()

    if args.max_messages < 1:
        safe_print("--max-messages must be at least 1")
        return 1

    try:
        settings = get_settings()
        topics = _resolve_topics(settings, topic=args.topic, full=args.full)
        return run(settings, topics=topics, max_messages=args.max_messages)
    except StorageError as exc:
        safe_print(f"Kafka → Bronze: FAILED — {exc}")
        return 1
    except Exception as exc:
        safe_print(f"Kafka → Bronze: FAILED — {exc}")
        logger.exception("kafka_to_bronze_once failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
