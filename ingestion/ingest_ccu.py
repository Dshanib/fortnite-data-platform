"""DEPRECATED: use ingestion.ingest_island_metrics for peak CCU via Ecosystem API."""

from __future__ import annotations

import sys
from typing import Optional

from common.logging import configure_logging, get_logger
from config.settings import Settings, get_settings

logger = get_logger(__name__)


def run_ingestion(settings: Optional[Settings] = None) -> None:
    """Deprecated entrypoint — redirects operators to island metrics ingestion."""
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    logger.error(
        "ingest_ccu is deprecated. Use: python -m ingestion.ingest_island_metrics"
    )
    sys.exit(1)


if __name__ == "__main__":
    run_ingestion()
