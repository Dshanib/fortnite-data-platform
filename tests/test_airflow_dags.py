"""Airflow DAG structure tests (no running scheduler required)."""

from __future__ import annotations

import compileall
import importlib.util
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DAG_FILES = (
    "fortnite_full_demo_dag.py",
    "fortnite_metrics_refresh_dag.py",
    "fortnite_shop_refresh_dag.py",
    "fortnite_reference_refresh_dag.py",
)

EXPECTED_DAG_IDS = {
    "fortnite_full_demo_dag",
    "fortnite_metrics_refresh_dag",
    "fortnite_shop_refresh_dag",
    "fortnite_reference_refresh_dag",
}

# Valid Fernet key shape for DagBag import tests only — never use in production.
_TEST_AIRFLOW_FERNET_KEY = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="


def test_dag_files_compile() -> None:
    for name in DAG_FILES:
        path = ROOT / "dags" / name
        assert path.is_file(), f"missing {path}"
        assert compileall.compile_file(str(path), quiet=1)


def test_dag_ids_declared() -> None:
    for name in DAG_FILES:
        text = (ROOT / "dags" / name).read_text(encoding="utf-8")
        assert 'dag_id="' in text or "dag_id='" in text


@pytest.mark.skipif(
    importlib.util.find_spec("airflow") is None,
    reason="apache-airflow not installed on host",
)
def test_dag_bag_imports_without_errors() -> None:
    os.environ.setdefault("FORTNITE_PROJECT_ROOT", str(ROOT))
    os.environ.setdefault("AIRFLOW_FERNET_KEY", _TEST_AIRFLOW_FERNET_KEY)
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from airflow.models import DagBag

    dagbag = DagBag(dag_folder=str(ROOT / "dags"), include_examples=False)
    assert not dagbag.import_errors, f"DAG import errors: {dagbag.import_errors}"
    loaded = {dag.dag_id for dag in dagbag.dags.values()}
    assert EXPECTED_DAG_IDS.issubset(loaded)
