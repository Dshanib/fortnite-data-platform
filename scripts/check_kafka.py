"""Kafka connectivity check script."""

from __future__ import annotations

import sys

from kafka import KafkaAdminClient
from kafka.errors import NoBrokersAvailable

from common.logging import configure_logging, get_logger
from config.settings import get_settings

logger = get_logger(__name__)


def main() -> int:
    """Verify Kafka bootstrap servers are reachable."""
    settings = get_settings()
    configure_logging(settings.log_level)
    servers = settings.kafka_bootstrap_servers.split(",")
    try:
        client = KafkaAdminClient(bootstrap_servers=servers, request_timeout_ms=10000)
        topics = client.list_topics()
        logger.info("Kafka OK bootstrap=%s topics=%s", servers, len(topics))
        client.close()
        return 0
    except NoBrokersAvailable as exc:
        logger.error("Kafka unreachable bootstrap=%s: %s", servers, exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
