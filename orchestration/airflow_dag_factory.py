"""Shared BashOperator builders for Fortnite Airflow DAGs."""

from __future__ import annotations

import os
from datetime import timedelta
from typing import Any, Dict, Optional, Sequence

from airflow.operators.bash import BashOperator

PROJECT_ROOT = os.environ.get("FORTNITE_PROJECT_ROOT", "/opt/airflow/project")
PYTHON_BIN = os.environ.get("FORTNITE_PYTHON", "python")

MAX_ISLANDS = os.environ.get("FORTNITE_MAX_ISLANDS", "50")
SERVING_MODE = os.environ.get("FORTNITE_SERVING_MODE", "direct_minio")
MAX_MESSAGES_PER_TOPIC = os.environ.get("FORTNITE_MAX_MESSAGES_PER_TOPIC", "20")

DEFAULT_TASK_ARGS: Dict[str, Any] = {
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
}

DEFAULT_DAG_ARGS: Dict[str, Any] = {
    "owner": "fortnite-de",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
}


def _shell_cmd(parts: Sequence[str]) -> str:
    quoted = " ".join(parts)
    return (
        f"cd {PROJECT_ROOT} && "
        f"export PYTHONPATH={PROJECT_ROOT} && "
        f"{PYTHON_BIN} {quoted}"
    ).strip()


def script_operator(
    dag: Any,
    task_id: str,
    script_name: str,
    *cli_args: str,
    execution_timeout: Optional[timedelta] = timedelta(minutes=45),
    extra_env: Optional[Dict[str, str]] = None,
    **kwargs: Any,
) -> BashOperator:
    """Run a file under scripts/ (e.g. check_minio.py)."""
    cmd = _shell_cmd([f"scripts/{script_name}", *cli_args])
    if extra_env:
        exports = " ".join(f'{k}="{v}"' for k, v in extra_env.items())
        cmd = f"export {exports} && {cmd}"
    return BashOperator(
        task_id=task_id,
        bash_command=cmd,
        dag=dag,
        execution_timeout=execution_timeout,
        **{**DEFAULT_TASK_ARGS, **kwargs},
    )


def module_operator(
    dag: Any,
    task_id: str,
    module: str,
    *cli_args: str,
    execution_timeout: Optional[timedelta] = timedelta(minutes=60),
    **kwargs: Any,
) -> BashOperator:
    """Run python -m <module> from project root."""
    cmd = _shell_cmd(["-m", module, *cli_args])
    return BashOperator(
        task_id=task_id,
        bash_command=cmd,
        dag=dag,
        execution_timeout=execution_timeout,
        **{**DEFAULT_TASK_ARGS, **kwargs},
    )


def kafka_to_bronze_operator(
    dag: Any,
    task_id: str,
    topic: Optional[str] = None,
    *,
    max_messages: Optional[str] = None,
    full: bool = False,
    **kwargs: Any,
) -> BashOperator:
    """Consume one Kafka topic (or --full for all topics) into MinIO bronze."""
    args: list[str] = []
    if full:
        args.append("--full")
    elif topic:
        args.extend(["--topic", topic])
    else:
        raise ValueError("kafka_to_bronze_operator requires topic= or full=True")
    args.extend(["--max-messages", max_messages or MAX_MESSAGES_PER_TOPIC])
    return script_operator(dag, task_id, "kafka_to_bronze_once.py", *args, **kwargs)


def bronze_to_silver_operator(dag: Any, **kwargs: Any) -> BashOperator:
    return script_operator(
        dag,
        "bronze_to_silver",
        "run_bronze_to_silver.py",
        "--engine",
        "python",
        execution_timeout=timedelta(minutes=60),
        **kwargs,
    )


def silver_to_gold_operator(dag: Any, **kwargs: Any) -> BashOperator:
    return script_operator(
        dag,
        "silver_to_gold",
        "run_silver_to_gold.py",
        "--engine",
        "python",
        execution_timeout=timedelta(minutes=45),
        **kwargs,
    )


def check_duckdb_operator(dag: Any, **kwargs: Any) -> BashOperator:
    return script_operator(
        dag,
        "check_duckdb_serving",
        "check_duckdb_serving.py",
        "--mode",
        SERVING_MODE,
        extra_env={"DUCKDB_GOLD_READ_MODE": SERVING_MODE},
        execution_timeout=timedelta(minutes=15),
        **kwargs,
    )
