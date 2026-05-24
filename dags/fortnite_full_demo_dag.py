"""Manual full end-to-end demo pipeline (equivalent to scripts/demo_run.py)."""

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

_demo_metrics_args: list[str] = []
if MAX_ISLANDS:
    _demo_metrics_args = ["--max-islands", MAX_ISLANDS]

with DAG(
    dag_id="fortnite_full_demo_dag",
    description="Full Fortnite lakehouse refresh for manual demo runs",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["fortnite", "data-engineering", "refresh", "demo"],
    default_args=DEFAULT_DAG_ARGS,
) as dag:
    check_minio = script_operator(dag, "check_minio", "check_minio.py", execution_timeout=timedelta(minutes=5))
    check_kafka = script_operator(dag, "check_kafka", "check_kafka.py", execution_timeout=timedelta(minutes=5))
    create_topics = script_operator(
        dag, "create_kafka_topics", "create_kafka_topics.py", execution_timeout=timedelta(minutes=5)
    )
    ingest_shop = module_operator(dag, "ingest_shop", "ingestion.ingest_shop")
    ingest_cosmetics = module_operator(dag, "ingest_cosmetics", "ingestion.ingest_cosmetics")
    ingest_islands = module_operator(dag, "ingest_islands", "ingestion.ingest_islands")
    ingest_metrics = module_operator(
        dag,
        "ingest_island_metrics",
        "ingestion.ingest_island_metrics",
        *_demo_metrics_args,
        execution_timeout=timedelta(hours=3),
    )
    kafka_all = kafka_to_bronze_operator(dag, "kafka_to_bronze_all_topics", full=True)
    bronze_silver = bronze_to_silver_operator(dag)
    silver_gold = silver_to_gold_operator(dag)
    duckdb_check = check_duckdb_operator(dag)

    check_minio >> create_topics >> check_kafka
    check_kafka >> [ingest_shop, ingest_cosmetics, ingest_islands, ingest_metrics]
    [ingest_shop, ingest_cosmetics, ingest_islands, ingest_metrics] >> kafka_all
    kafka_all >> bronze_silver >> silver_gold >> duckdb_check
