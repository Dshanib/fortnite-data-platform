#!/usr/bin/env python3
"""Create Kafka topics for Phase 1 (idempotent)."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from kafka import KafkaAdminClient
from kafka.admin import NewTopic
from kafka.errors import KafkaError, NoBrokersAvailable, TopicAlreadyExistsError

from scripts._script_runtime import bootstrap, safe_print

bootstrap()

from common.logging import configure_logging, get_logger
from config.settings import get_settings

logger = get_logger(__name__)


def _topic_names(settings) -> list[str]:
    return [
        settings.kafka_topic_shop,
        settings.kafka_topic_cosmetics,
        settings.kafka_topic_islands,
        settings.kafka_topic_island_metrics,
        settings.kafka_topic_ingestion_status,
    ]


def main() -> int:
    """Create configured Kafka topics if they do not exist."""
    try:
        settings = get_settings()
        configure_logging(settings.log_level)
        bootstrap_servers = settings.kafka_bootstrap_servers.split(",")
        topics = _topic_names(settings)

        admin = KafkaAdminClient(
            bootstrap_servers=bootstrap_servers,
            request_timeout_ms=15000,
        )

        safe_print(f"Kafka bootstrap: {settings.kafka_bootstrap_servers}")
        for name in topics:
            try:
                admin.create_topics([NewTopic(name=name, num_partitions=1, replication_factor=1)])
                safe_print(f"  {name}: created")
            except TopicAlreadyExistsError:
                safe_print(f"  {name}: exists")
            except KafkaError as exc:
                safe_print(f"  {name}: error — {exc}")
                admin.close()
                return 1

        admin.close()
        safe_print("Topic setup complete.")
        return 0
    except NoBrokersAvailable:
        safe_print("Kafka connection failed: no broker available at KAFKA_BOOTSTRAP_SERVERS.")
        safe_print("Start infra: docker compose --env-file .env up -d zookeeper kafka")
        return 1
    except Exception as exc:
        safe_print(f"Topic setup failed: {exc}")
        logger.exception("create_kafka_topics failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
