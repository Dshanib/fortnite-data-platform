#!/usr/bin/env python3
"""Run batch Bronze JSON → Silver Parquet job on MinIO."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts._script_runtime import bootstrap, safe_print

bootstrap()


def _print_results(results, failures: int) -> int:
    for result in results:
        safe_print(f"\nsource: {result.source}")
        safe_print(f"  silver_dataset: {result.silver_dataset}")
        safe_print(f"  bronze_events: {result.input_count}")
        safe_print(f"  silver_rows: {result.output_count}")
        safe_print(f"  target_path: {result.target_path}")
        safe_print(f"  status: {result.status}")
        if result.status == "no_rows" and result.input_count > 0:
            failures += 1
        if result.input_count == 0:
            safe_print("  note: no bronze files — run kafka_to_bronze_once.py first")
    safe_print(f"\nBronze → Silver: {'SUCCESS' if failures == 0 else 'PARTIAL'}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Bronze JSON → Silver Parquet (batch).")
    parser.add_argument(
        "--sources",
        help="Comma-separated bronze sources: shop,cosmetics,islands,island_metrics",
    )
    parser.add_argument(
        "--engine",
        choices=("python", "spark"),
        default="python",
        help="python=MinIO+PyArrow (fast, default); spark=PySpark S3A (slow first run)",
    )
    args = parser.parse_args()

    from config.settings import get_settings

    settings = get_settings()
    sources = [s.strip() for s in args.sources.split(",") if s.strip()] if args.sources else None

    safe_print(
        f"MinIO profile={settings.minio_profile} "
        f"endpoint={settings.minio_endpoint} bucket={settings.minio_bucket}"
    )
    safe_print(f"Engine: {args.engine}")
    if sources:
        safe_print(f"Sources: {', '.join(sources)}")

    failures = 0

    if args.engine == "python":
        try:
            import pyarrow  # noqa: F401
            import pandas  # noqa: F401
        except ImportError:
            safe_print("Install: pip install pandas pyarrow")
            return 1

        from streaming.bronze_to_silver_local import run_job_local

        safe_print("\nReading bronze from MinIO and writing silver Parquet...")
        results = run_job_local(settings, sources=sources)
        failures = _print_results(results, failures)
        return 1 if failures else 0

    try:
        from pyspark.sql import SparkSession  # noqa: F401
    except ImportError:
        safe_print("PySpark not installed. Use --engine python or: pip install pyspark")
        return 1

    from streaming.job_bronze_to_silver import run_job
    from streaming.spark_session import build_spark_session

    safe_print("\nStarting Spark (first run may download JARs for 5–10 minutes)...")
    spark = build_spark_session(settings)
    try:
        results = run_job(spark, settings, sources=sources)
    finally:
        spark.stop()

    failures = _print_results(results, failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
