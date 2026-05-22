#!/usr/bin/env python3
"""Initialize DuckDB serving layer and run predefined QueryService checks."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts._script_runtime import bootstrap, safe_print

bootstrap()

from common.logging import configure_logging, get_logger
from config.settings import get_settings, load_settings
from serving.duckdb_init import init_duckdb, view_exists
from serving.gold_paths import resolve_gold_paths
from serving.gold_sync import sync_gold_from_minio
from serving.minio_duckdb import GOLD_READ_MODE_DIRECT, GOLD_READ_MODE_LOCAL
from serving.query_service import QueryService

logger = get_logger(__name__)


def _print_response(response) -> None:
    safe_print(f"\n{response.query_name} [{response.status}]")
    safe_print(f"  message: {response.message}")
    if response.data:
        preview = response.data[:3]
        safe_print(f"  rows: {len(response.data)}")
        safe_print(f"  sample: {json.dumps(preview, default=str, indent=2)}")
    else:
        safe_print("  rows: 0")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check DuckDB Gold serving layer.")
    parser.add_argument(
        "--mode",
        choices=(GOLD_READ_MODE_DIRECT, GOLD_READ_MODE_LOCAL),
        default=None,
        help="Gold read mode (overrides DUCKDB_GOLD_READ_MODE)",
    )
    parser.add_argument(
        "--skip-sync",
        action="store_true",
        help="Do not download Gold Parquet (local_cache only; ignored for direct_minio)",
    )
    args = parser.parse_args()

    if args.mode:
        os.environ["DUCKDB_GOLD_READ_MODE"] = args.mode
    settings = load_settings(reload=True)
    configure_logging(settings.log_level)

    active_mode = settings.duckdb_gold_read_mode
    safe_print(f"Active mode: {active_mode}")
    safe_print(f"DuckDB path: {settings.duckdb_path}")
    safe_print(f"Gold data root: {settings.gold_data_root}")

    if active_mode == GOLD_READ_MODE_LOCAL and not args.skip_sync:
        safe_print("\nSyncing Gold Parquet from MinIO to local cache...")
        try:
            count = sync_gold_from_minio(settings)
            safe_print(f"  downloaded: {count} parquet file(s)")
        except Exception as exc:
            safe_print(f"  sync warning: {exc}")
            safe_print("  continuing with existing local Gold paths")
    elif active_mode == GOLD_READ_MODE_DIRECT:
        safe_print("\nSkipping local Gold sync (direct_minio mode)")

    paths = resolve_gold_paths(settings, mode=active_mode)
    safe_print(f"\nResolved Gold paths (mode={paths.read_mode}):")
    for name, glob_path in paths.as_dict().items():
        safe_print(f"  {name}: {glob_path or '(missing)'}")

    safe_print("\nInitializing DuckDB views...")
    conn = init_duckdb(settings, mode=active_mode)
    for view in (
        "vw_current_island_activity",
        "vw_top_islands_by_peak_ccu",
        "vw_island_metric_hourly",
        "vw_shop_rarity_distribution",
        "vw_source_health_summary",
    ):
        safe_print(f"  {view}: {'OK' if view_exists(conn, view) else 'missing'}")
    conn.close()

    service = QueryService(settings, auto_init=False)
    checks = [
        service.get_current_ccu,
        lambda: service.get_top_islands(10),
        service.get_avg_today,
        service.get_recent_anomalies,
        service.get_shop_rarity_distribution,
        service.get_source_health,
    ]

    safe_print("\nRunning QueryService checks...")
    errors = 0
    for fn in checks:
        response = fn()
        _print_response(response)
        if response.status == "error":
            errors += 1

    safe_print(
        f"\nDuckDB serving check: "
        f"{'SUCCESS' if errors == 0 else 'PARTIAL (see errors above)'}"
    )
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
