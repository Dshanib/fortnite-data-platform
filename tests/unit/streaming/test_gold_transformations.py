"""Gold transformation unit tests."""

from __future__ import annotations

import pandas as pd

from streaming.gold_transformations import (
    build_current_island_activity,
    build_island_activity_anomalies,
    build_island_metric_hourly,
    build_shop_rarity_distribution,
    build_source_health_summary,
    build_top_islands_by_peak_ccu,
)


def test_build_current_island_activity_pivot() -> None:
    metrics = pd.DataFrame(
        [
            {
                "island_code": "A",
                "metric_name": "peakCCU",
                "metric_timestamp": "2026-05-17T10:00:00Z",
                "metric_value": 10.0,
            },
            {
                "island_code": "A",
                "metric_name": "peakCCU",
                "metric_timestamp": "2026-05-17T11:00:00Z",
                "metric_value": 20.0,
            },
            {
                "island_code": "A",
                "metric_name": "plays",
                "metric_timestamp": "2026-05-17T11:00:00Z",
                "metric_value": 5.0,
            },
        ]
    )
    islands = pd.DataFrame(
        [{"island_code": "A", "title": "Island A", "creator_code": "creator1"}]
    )
    result = build_current_island_activity(metrics, islands)
    assert len(result) == 1
    assert result.iloc[0]["peak_ccu"] == 20.0
    assert result.iloc[0]["plays"] == 5.0
    assert result.iloc[0]["title"] == "Island A"


def test_build_top_islands_by_peak_ccu() -> None:
    activity = pd.DataFrame(
        [
            {
                "island_code": "A",
                "title": "A",
                "peak_ccu": 50,
                "unique_players": 1,
                "plays": 1,
                "latest_metric_timestamp": "t1",
            },
            {
                "island_code": "B",
                "title": "B",
                "peak_ccu": 100,
                "unique_players": 2,
                "plays": 2,
                "latest_metric_timestamp": "t2",
            },
        ]
    )
    top = build_top_islands_by_peak_ccu(activity, top_n=1)
    assert len(top) == 1
    assert top.iloc[0]["rank"] == 1
    assert top.iloc[0]["island_code"] == "B"


def test_build_island_metric_hourly_null_safe() -> None:
    metrics = pd.DataFrame(
        [
            {
                "island_code": "A",
                "metric_name": "peakCCU",
                "metric_timestamp": "2026-05-17T10:15:00Z",
                "metric_value": 10.0,
            },
            {
                "island_code": "A",
                "metric_name": "peakCCU",
                "metric_timestamp": "2026-05-17T10:45:00Z",
                "metric_value": None,
            },
        ]
    )
    hourly = build_island_metric_hourly(metrics)
    assert len(hourly) == 1
    assert hourly.iloc[0]["sample_count"] == 2
    assert hourly.iloc[0]["avg_value"] == 10.0
    assert pd.isna(hourly.iloc[0]["min_value"]) or hourly.iloc[0]["min_value"] == 10.0


def test_build_shop_rarity_distribution() -> None:
    shop = pd.DataFrame(
        [
            {"snapshot_date": "2026-05-17", "dev_name": "c1", "offer_id": "o1"},
            {"snapshot_date": "2026-05-17", "dev_name": "c2", "offer_id": "o2"},
        ]
    )
    cosmetics = pd.DataFrame(
        [
            {"cosmetic_id": "c1", "rarity": "epic"},
            {"cosmetic_id": "c2", "rarity": "rare"},
        ]
    )
    dist = build_shop_rarity_distribution(shop, cosmetics)
    assert dist["item_count"].sum() == 2
    assert abs(dist["share_pct"].sum() - 100.0) < 0.01


def test_build_island_activity_anomalies_spike() -> None:
    metrics = pd.DataFrame(
        [
            {
                "island_code": "A",
                "metric_name": "peakCCU",
                "metric_timestamp": "2026-05-17T10:00:00Z",
                "metric_value": 10.0,
            },
            {
                "island_code": "A",
                "metric_name": "peakCCU",
                "metric_timestamp": "2026-05-17T11:00:00Z",
                "metric_value": 20.0,
            },
            {
                "island_code": "A",
                "metric_name": "peakCCU",
                "metric_timestamp": "2026-05-17T12:00:00Z",
                "metric_value": 50.0,
            },
        ]
    )
    islands = pd.DataFrame([{"island_code": "A", "title": "Spike Island"}])
    anomalies = build_island_activity_anomalies(metrics, islands)
    assert len(anomalies) >= 1
    latest = anomalies.iloc[0]
    assert latest["peak_ccu"] == 50.0
    assert latest["severity"] in ("medium", "high")
    assert latest["title"] == "Spike Island"


def test_build_island_activity_anomalies_empty_without_spike() -> None:
    metrics = pd.DataFrame(
        [
            {
                "island_code": "B",
                "metric_name": "peakCCU",
                "metric_timestamp": "2026-05-17T10:00:00Z",
                "metric_value": 10.0,
            },
            {
                "island_code": "B",
                "metric_name": "peakCCU",
                "metric_timestamp": "2026-05-17T11:00:00Z",
                "metric_value": 11.0,
            },
        ]
    )
    anomalies = build_island_activity_anomalies(metrics)
    assert anomalies.empty


def test_build_source_health_summary() -> None:
    events = [
        {
            "source": "fortnite_api_com",
            "entity": "shop",
            "status": "success",
            "observed_at": "2026-05-17T10:00:00Z",
        },
        {
            "source": "fortnite_api_com",
            "entity": "cosmetics",
            "status": "failed",
            "observed_at": "2026-05-17T11:00:00Z",
        },
    ]
    summary = build_source_health_summary(events)
    assert len(summary) == 1
    assert summary.iloc[0]["success_count"] == 1
    assert summary.iloc[0]["failure_count"] == 1
