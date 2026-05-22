#!/usr/bin/env python3
"""One-shot demo runbook: validate infra, refresh data, check DuckDB serving."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from typing import List

from scripts._script_runtime import bootstrap, safe_print

bootstrap()

from scripts.pipeline_runner import (
    StepFailed,
    kafka_topics_from_settings,
    run_module,
    run_python_script,
)


@dataclass
class DemoSummary:
    """Collected notes for the final demo summary."""

    sources_refreshed: List[str] = field(default_factory=list)
    bronze_topics: List[str] = field(default_factory=list)
    silver_ok: bool = False
    gold_ok: bool = False
    serving_mode: str = "direct_minio"
    serving_ok: bool = False
    duckdb_message: str = ""


def _step_banner(title: str) -> None:
    safe_print("\n" + "=" * 60)
    safe_print(title)
    safe_print("=" * 60)


def _run_ingestion(summary: DemoSummary) -> None:
    _step_banner("Step 3 — API ingestion (once)")
    for name, module in (
        ("shop", "ingestion.ingest_shop"),
        ("cosmetics", "ingestion.ingest_cosmetics"),
        ("islands", "ingestion.ingest_islands"),
    ):
        code = run_module(module, critical=True)
        if code == 0:
            summary.sources_refreshed.append(name)

    safe_print("\n--- island_metrics (all islands) ---")
    code = run_module("ingestion.ingest_island_metrics", critical=True)
    if code == 0:
        summary.sources_refreshed.append("island_metrics")


def _run_kafka_to_bronze(max_messages: int, summary: DemoSummary) -> None:
    _step_banner("Step 5 — Kafka → Bronze")
    for topic in kafka_topics_from_settings():
        run_python_script(
            "kafka_to_bronze_once.py",
            "--topic",
            topic,
            "--max-messages",
            str(max_messages),
            critical=True,
        )
        summary.bronze_topics.append(topic)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the full demo pipeline end-to-end (does not start the bot).",
    )
    parser.add_argument(
        "--skip-ingestion",
        action="store_true",
        help="Skip API ingestion steps",
    )
    parser.add_argument(
        "--skip-kafka-to-bronze",
        action="store_true",
        help="Skip Kafka → Bronze consumer",
    )
    parser.add_argument(
        "--skip-spark",
        action="store_true",
        help="Skip Bronze→Silver and Silver→Gold transforms",
    )
    parser.add_argument(
        "--serving-mode",
        choices=("direct_minio", "local_cache"),
        default="direct_minio",
        help="DuckDB Gold read mode for serving check",
    )
    parser.add_argument(
        "--max-messages-per-topic",
        type=int,
        default=20,
        help="Max Kafka messages per topic for bronze write (default: 20)",
    )
    args = parser.parse_args()

    if args.max_messages_per_topic < 1:
        safe_print("--max-messages-per-topic must be at least 1")
        return 1

    summary = DemoSummary(serving_mode=args.serving_mode)

    try:
        _step_banner("Step 1 — Validate MinIO")
        run_python_script("check_minio.py", critical=True)

        _step_banner("Step 2 — Validate Kafka")
        run_python_script("check_kafka.py", critical=True)

        if not args.skip_ingestion:
            _run_ingestion(summary)
        else:
            safe_print("\n[skip] API ingestion")

        _step_banner("Step 4 — Validate Kafka (post-ingestion)")
        run_python_script("check_kafka.py", critical=False)

        if not args.skip_kafka_to_bronze:
            _run_kafka_to_bronze(args.max_messages_per_topic, summary)
        else:
            safe_print("\n[skip] Kafka → Bronze")

        if not args.skip_spark:
            _step_banner("Step 6 — Bronze → Silver")
            code = run_python_script(
                "run_bronze_to_silver.py",
                "--engine",
                "python",
                critical=True,
            )
            summary.silver_ok = code == 0

            _step_banner("Step 7 — Silver → Gold")
            code = run_python_script(
                "run_silver_to_gold.py",
                "--engine",
                "python",
                critical=True,
            )
            summary.gold_ok = code == 0
        else:
            safe_print("\n[skip] Bronze→Silver and Silver→Gold")

        _step_banner("Step 8 — Validate DuckDB serving")
        duck_args = ["--mode", args.serving_mode]
        code = run_python_script(
            "check_duckdb_serving.py",
            *duck_args,
            env={"DUCKDB_GOLD_READ_MODE": args.serving_mode},
            critical=True,
        )
        summary.serving_ok = code == 0
        summary.duckdb_message = "SUCCESS" if code == 0 else "FAILED"

    except StepFailed as exc:
        safe_print(f"\nDemo run stopped: {exc}")
        return exc.code or 1
    except Exception as exc:
        safe_print(f"\nDemo run stopped: {exc}")
        return 1

    _step_banner("Step 9 — Demo summary")
    safe_print(f"Sources refreshed: {', '.join(summary.sources_refreshed) or '(skipped)'}")
    safe_print(
        f"Bronze topics written: {', '.join(summary.bronze_topics) or '(skipped)'}"
    )
    safe_print(f"Silver updated: {'yes' if summary.silver_ok else 'skipped/no'}")
    safe_print(f"Gold updated: {'yes' if summary.gold_ok else 'skipped/no'}")
    safe_print(
        f"DuckDB serving ({summary.serving_mode}): {summary.duckdb_message or 'checked'}"
    )
    safe_print("\nStart the Telegram bot in a separate terminal:")
    safe_print("  python -m bot.app")
    safe_print("\nDemo run: SUCCESS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
