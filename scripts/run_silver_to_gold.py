#!/usr/bin/env python3
"""Run Silver Parquet → Gold analytical Parquet on MinIO."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts._script_runtime import bootstrap, safe_print

bootstrap()


def _top_n_from_env() -> int | None:
    raw = os.getenv("FORTNITE_GOLD_TOP_ISLANDS_N", "").strip()
    if not raw:
        return None
    try:
        value = int(raw)
        return value if value > 0 else None
    except ValueError:
        return None


def _print_results(results) -> int:
    failures = 0
    for result in results:
        safe_print(f"\ndataset: {result.name}")
        safe_print(f"  input_count: {result.input_count}")
        safe_print(f"  output_count: {result.output_count}")
        safe_print(f"  target_path: {result.target_path}")
        safe_print(f"  status: {result.status}")
        if result.name == "current_island_activity" and result.status == "empty":
            failures += 1
    safe_print(f"\nSilver → Gold: {'SUCCESS' if failures == 0 else 'FAILED'}")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Silver Parquet → Gold Parquet.")
    parser.add_argument(
        "--engine",
        choices=("python", "spark"),
        default="python",
        help="python=MinIO+PyArrow (fast); spark=PySpark S3A",
    )
    parser.add_argument(
        "--top-islands",
        type=int,
        default=None,
        help="Limit top_islands_by_peak_ccu rows (default: all)",
    )
    args = parser.parse_args()

    from common.exceptions import StorageError
    from common.logging import get_logger
    from config.settings import get_settings

    logger = get_logger(__name__)
    settings = get_settings()
    top_n = args.top_islands if args.top_islands and args.top_islands > 0 else _top_n_from_env()

    safe_print(
        f"MinIO profile={settings.minio_profile} "
        f"endpoint={settings.minio_endpoint} bucket={settings.minio_bucket}"
    )
    safe_print(f"Engine: {args.engine}")

    try:
        if args.engine == "python":
            from streaming.silver_to_gold_local import run_job_local

            safe_print("\nBuilding gold datasets from silver Parquet...")
            results = run_job_local(settings, top_islands_n=top_n)
            return _print_results(results)

        from streaming.job_silver_to_gold import run_job
        from streaming.spark_session import build_spark_session

        safe_print("\nStarting Spark (first run may take several minutes)...")
        spark = build_spark_session(settings, app_name="fortnite-silver-to-gold")
        try:
            results = run_job(spark, settings, top_islands_n=top_n)
        finally:
            spark.stop()
        return _print_results(results)

    except StorageError as exc:
        safe_print(f"Silver → Gold: FAILED — {exc}")
        return 1
    except Exception as exc:
        safe_print(f"Silver → Gold: FAILED — {exc}")
        logger.exception("run_silver_to_gold failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
