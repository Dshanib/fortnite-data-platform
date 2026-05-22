"""Frequent island metrics refresh (near-real-time activity)."""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG

from orchestration.airflow_dag_factory import (
    DEFAULT_DAG_ARGS,
    MAX_ISLANDS,
    bronze_to_silver_operator,
    check_duckdb_operator,
    kafka_to_bronze_operator,
    module_operator,
    script_operator,
    silver_to_gold_operator,
)

with DAG(
    dag_id="fortnite_metrics_refresh_dag",
    description="Refresh island metrics: ingest → bronze → silver → gold → DuckDB",
    schedule=timedelta(minutes=5),
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["fortnite", "data-engineering", "refresh", "metrics"],
    default_args=DEFAULT_DAG_ARGS,
) as dag:
    check_kafka = script_operator(dag, "check_kafka", "check_kafka.py", execution_timeout=timedelta(minutes=5))
    check_minio = script_operator(dag, "check_minio", "check_minio.py", execution_timeout=timedelta(minutes=5))
    ingest_metrics = module_operator(
        dag,
        "ingest_island_metrics",
        "ingestion.ingest_island_metrics",
        "--max-islands",
        MAX_ISLANDS,
        execution_timeout=timedelta(minutes=90),
    )
    kafka_metrics = kafka_to_bronze_operator(
        dag,
        "kafka_to_bronze_island_metrics",
        "fortnite.raw.island_metrics",
    )
    kafka_health = kafka_to_bronze_operator(
        dag,
        "kafka_to_bronze_ingestion_status",
        "fortnite.ops.ingestion_status",
    )
    bronze_silver = bronze_to_silver_operator(dag)
    silver_gold = silver_to_gold_operator(dag)
    duckdb_check = check_duckdb_operator(dag)

    [check_kafka, check_minio] >> ingest_metrics
    ingest_metrics >> kafka_metrics >> kafka_health
    kafka_health >> bronze_silver >> silver_gold >> duckdb_check
