#!/usr/bin/env python3
"""
Deprecated: replaced by Airflow DAG orchestration.

Kept for fallback/local debugging when Airflow is not running.
Primary schedulers:
  - fortnite_metrics_refresh_dag (every 5 minutes)
  - fortnite_shop_refresh_dag (every 60 minutes)
  - fortnite_reference_refresh_dag (daily)

See docs/airflow_orchestration.md.
"""

from __future__ import annotations

import argparse
import signal
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts._script_runtime import bootstrap, safe_print

bootstrap()

from scripts.pipeline_runner import (
    StepFailed,
    kafka_topics_from_settings,
    run_module,
    run_python_script,
)

_stop = False


def _handle_sigint(_signum: int, _frame: object) -> None:
    global _stop
    _stop = True
    safe_print("\nShutdown requested — finishing after current step...")


def run_cycle(
    *,
    max_messages: int,
    serving_mode: str,
    skip_ingestion: bool,
    max_islands: int | None,
) -> bool:
    """Run one refresh cycle. Returns False if a critical step failed."""
    cycle_start = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    safe_print(f"\n{'=' * 60}\nRefresh cycle @ {cycle_start}\n{'=' * 60}")

    try:
        if not skip_ingestion:
            run_module("ingestion.ingest_shop", critical=False)
            run_module("ingestion.ingest_cosmetics", critical=False)
            run_module("ingestion.ingest_islands", critical=False)
            metrics_args: list[str] = []
            if max_islands is not None and max_islands > 0:
                metrics_args = ["--max-islands", str(max_islands)]
            run_module("ingestion.ingest_island_metrics", *metrics_args, critical=False)
        else:
            safe_print("[skip] ingestion")

        for topic in kafka_topics_from_settings():
            run_python_script(
                "kafka_to_bronze_once.py",
                "--topic",
                topic,
                "--max-messages",
                str(max_messages),
                critical=False,
            )

        run_python_script(
            "run_bronze_to_silver.py",
            "--engine",
            "python",
            critical=False,
        )
        run_python_script(
            "run_silver_to_gold.py",
            "--engine",
            "python",
            critical=False,
        )

        duck_args = ["--mode", serving_mode]
        run_python_script(
            "check_duckdb_serving.py",
            *duck_args,
            env={"DUCKDB_GOLD_READ_MODE": serving_mode},
            critical=False,
        )
        return True
    except StepFailed as exc:
        safe_print(f"Cycle warning: {exc}")
        return False


def main() -> int:
    safe_print(
        "WARNING: scripts/deprecated/continuous_refresh.py is deprecated. "
        "Use Airflow DAGs (see docs/airflow_orchestration.md)."
    )
    parser = argparse.ArgumentParser(
        description="[DEPRECATED] Continuously refresh ingestion and lakehouse layers.",
    )
    parser.add_argument("--interval-seconds", type=int, default=300)
    parser.add_argument(
        "--serving-mode",
        choices=("direct_minio", "local_cache"),
        default="direct_minio",
    )
    parser.add_argument("--max-messages-per-topic", type=int, default=20)
    parser.add_argument("--skip-ingestion", action="store_true")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--max-islands", type=int, default=50)
    args = parser.parse_args()

    if args.interval_seconds < 1:
        safe_print("--interval-seconds must be at least 1")
        return 1

    signal.signal(signal.SIGINT, _handle_sigint)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _handle_sigint)

    max_islands = args.max_islands if args.max_islands > 0 else None

    while not _stop:
        run_cycle(
            max_messages=args.max_messages_per_topic,
            serving_mode=args.serving_mode,
            skip_ingestion=args.skip_ingestion,
            max_islands=max_islands,
        )
        if args.once:
            break
        if _stop:
            break
        safe_print(f"\nSleeping {args.interval_seconds}s until next cycle...")
        for _ in range(args.interval_seconds):
            if _stop:
                break
            time.sleep(1)

    safe_print("\nContinuous refresh stopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
