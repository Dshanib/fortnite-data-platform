"""QueryService tests (no_data behavior and deterministic queries)."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
import pytest

from config.settings import get_settings
from serving.duckdb_init import refresh_views, view_exists
from serving.query_service import QueryService


def _write_gold_parquet(root: Path, dataset: str, frame: pd.DataFrame) -> None:
    out_dir = root / dataset
    out_dir.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(out_dir / f"{dataset}.parquet", index=False)


@pytest.fixture
def gold_root(tmp_path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "gold"
    monkeypatch.setenv("GOLD_DATA_ROOT", str(root))
    get_settings.cache_clear()

    _write_gold_parquet(
        root,
        "current_island_activity",
        pd.DataFrame(
            [
                {
                    "island_code": "A",
                    "title": "Island A",
                    "creator_code": "c1",
                    "latest_metric_timestamp": "2026-05-17T12:00:00Z",
                    "peak_ccu": 100.0,
                    "unique_players": 50.0,
                    "plays": 10.0,
                    "minutes_played": 200.0,
                    "updated_at": "2026-05-17T12:00:00Z",
                },
                {
                    "island_code": "B",
                    "title": "Island B",
                    "creator_code": "c2",
                    "latest_metric_timestamp": "2026-05-17T12:00:00Z",
                    "peak_ccu": 80.0,
                    "unique_players": 40.0,
                    "plays": 8.0,
                    "minutes_played": 150.0,
                    "updated_at": "2026-05-17T12:00:00Z",
                },
            ]
        ),
    )
    _write_gold_parquet(
        root,
        "top_islands_by_peak_ccu",
        pd.DataFrame(
            [
                {
                    "rank": 1,
                    "island_code": "A",
                    "title": "Island A",
                    "peak_ccu": 100.0,
                    "unique_players": 50.0,
                    "plays": 10.0,
                    "latest_metric_timestamp": "2026-05-17T12:00:00Z",
                }
            ]
        ),
    )
    _write_gold_parquet(
        root,
        "island_metric_hourly",
        pd.DataFrame(
            [
                {
                    "island_code": "A",
                    "metric_name": "peakCCU",
                    "metric_hour": "2026-05-17 12:00:00+00:00",
                    "avg_value": 90.0,
                    "min_value": 80.0,
                    "max_value": 100.0,
                    "sample_count": 3,
                }
            ]
        ),
    )
    _write_gold_parquet(
        root,
        "shop_rarity_distribution",
        pd.DataFrame(
            [
                {
                    "snapshot_date": "2026-05-17",
                    "rarity": "epic",
                    "item_count": 5,
                    "share_pct": 50.0,
                    "updated_at": "2026-05-17T12:00:00Z",
                }
            ]
        ),
    )
    _write_gold_parquet(
        root,
        "island_activity_anomalies",
        pd.DataFrame(
            [
                {
                    "island_code": "A",
                    "title": "Island A",
                    "metric_timestamp": "2026-05-17T13:00:00Z",
                    "peak_ccu": 200.0,
                    "previous_peak_ccu": 80.0,
                    "rolling_avg_peak_ccu": 90.0,
                    "pct_change_from_previous": 1.5,
                    "deviation_from_rolling_avg": 110.0,
                    "anomaly_type": "spike_vs_previous",
                    "severity": "high",
                    "detected_at": "2026-05-17T13:00:00Z",
                }
            ]
        ),
    )
    _write_gold_parquet(
        root,
        "source_health_summary",
        pd.DataFrame(
            [
                {
                    "source_name": "shop",
                    "last_success_at": "2026-05-17T12:00:00Z",
                    "last_failure_at": None,
                    "success_count": 2,
                    "failure_count": 0,
                    "latest_status": "success",
                }
            ]
        ),
    )
    yield root
    get_settings.cache_clear()


def test_query_service_no_data_when_gold_missing(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOLD_DATA_ROOT", str(tmp_path / "empty_gold"))
    monkeypatch.setenv("DUCKDB_PATH", str(tmp_path / "empty.duckdb"))
    get_settings.cache_clear()

    service = QueryService(get_settings(), auto_init=True)
    response = service.get_current_ccu()
    assert response.status == "no_data"
    assert response.data == []
    assert not response.success


def test_query_service_reads_gold_views(gold_root: Path, tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = tmp_path / "serving.duckdb"
    monkeypatch.setenv("DUCKDB_PATH", str(db_path))
    get_settings.cache_clear()
    settings = get_settings()

    conn = duckdb.connect(str(db_path))
    refresh_views(conn, settings)
    assert view_exists(conn, "vw_current_island_activity")
    conn.close()

    service = QueryService(settings, auto_init=False)

    ccu = service.get_current_ccu()
    assert ccu.status == "ok"
    assert ccu.data[0]["island_code"] == "A"
    assert ccu.data[0]["total_peak_ccu"] == 180.0

    top = service.get_top_islands(limit=5)
    assert top.status == "ok"
    assert top.data[0]["peak_ccu"] == 100.0

    shop = service.get_shop_rarity_distribution()
    assert shop.status == "ok"
    assert shop.data[0]["rarity"] == "epic"

    health = service.get_source_health()
    assert health.status == "ok"
    assert health.data[0]["source_name"] == "shop"

    anomalies = service.get_recent_anomalies(limit=5)
    assert anomalies.status == "ok"
    assert anomalies.data[0]["island_code"] == "A"
    assert anomalies.data[0]["severity"] == "high"


def test_get_avg_today_no_data_when_no_today_rows(gold_root: Path, tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DUCKDB_PATH", str(tmp_path / "avg.duckdb"))
    get_settings.cache_clear()
    service = QueryService(get_settings(), auto_init=True)
    response = service.get_avg_today()
    assert response.status == "no_data"
