#!/usr/bin/env python3
"""Run each API ingestion pipeline once (metrics limited to one island)."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts._script_runtime import bootstrap, safe_print

bootstrap()

from common.logging import configure_logging, get_logger
from config.settings import get_settings
from ingestion import (
    ingest_cosmetics,
    ingest_island_metrics,
    ingest_islands,
    ingest_shop,
)

logger = get_logger(__name__)


def main() -> int:
    """Run shop, cosmetics, islands, and single-island metrics ingestion."""
    settings = get_settings()
    configure_logging(settings.log_level)
    safe_print("Running all ingestion pipelines once...\n")

    steps = [
        ("shop", ingest_shop.run_ingestion),
        ("cosmetics", ingest_cosmetics.run_ingestion),
        ("islands", ingest_islands.run_ingestion),
        (
            "island_metrics",
            lambda s=settings: ingest_island_metrics.run_ingestion(s, max_islands=1),
        ),
    ]

    failures = 0
    for name, runner in steps:
        safe_print(f"--- {name} ---")
        code = runner(settings)
        if code != 0:
            failures += 1

    safe_print(f"\nAll ingestion complete. failures={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
