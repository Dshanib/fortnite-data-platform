"""Gold analytical transforms (pandas logic, testable without Spark)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd

from common.logging import get_logger

logger = get_logger(__name__)

METRIC_TO_COLUMN = {
    "peakCCU": "peak_ccu",
    "uniquePlayers": "unique_players",
    "plays": "plays",
    "minutesPlayed": "minutes_played",
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _empty_frame(columns: List[str]) -> pd.DataFrame:
    return pd.DataFrame(columns=columns)


def build_current_island_activity(
    metrics: pd.DataFrame,
    islands: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """Latest metric per island pivoted to columns; optional islands enrichment."""
    required = {"island_code", "metric_name", "metric_timestamp", "metric_value"}
    if metrics is None or metrics.empty or not required.issubset(metrics.columns):
        return _empty_frame(
            [
                "island_code",
                "title",
                "creator_code",
                "latest_metric_timestamp",
                "peak_ccu",
                "unique_players",
                "plays",
                "minutes_played",
                "updated_at",
            ]
        )

    work = metrics.copy()
    work["metric_timestamp"] = pd.to_datetime(work["metric_timestamp"], utc=True, errors="coerce")
    work = work.dropna(subset=["island_code", "metric_name", "metric_timestamp"])
    if work.empty:
        return _empty_frame(
            [
                "island_code",
                "title",
                "creator_code",
                "latest_metric_timestamp",
                "peak_ccu",
                "unique_players",
                "plays",
                "minutes_played",
                "updated_at",
            ]
        )

    work["_has_value"] = work["metric_value"].notna()
    latest = (
        work.sort_values(["_has_value", "metric_timestamp"], ascending=[False, False])
        .drop_duplicates(subset=["island_code", "metric_name"], keep="first")
    )
    pivot = latest.pivot_table(
        index="island_code",
        columns="metric_name",
        values="metric_value",
        aggfunc="first",
        dropna=False,
    )
    pivot.columns = [METRIC_TO_COLUMN.get(str(c), str(c)) for c in pivot.columns]
    pivot = pivot.reset_index()

    ts = (
        latest.groupby("island_code")["metric_timestamp"]
        .max()
        .reset_index()
        .rename(columns={"metric_timestamp": "latest_metric_timestamp"})
    )
    result = pivot.merge(ts, on="island_code", how="left")

    for col in ("peak_ccu", "unique_players", "plays", "minutes_played"):
        if col not in result.columns:
            result[col] = None

    if islands is not None and not islands.empty and "island_code" in islands.columns:
        meta = islands.drop_duplicates(subset=["island_code"])[
            ["island_code", "title", "creator_code"]
        ]
        result = result.merge(meta, on="island_code", how="left")
    else:
        if islands is None or islands.empty:
            logger.warning("Islands silver missing; gold activity without title/creator")
        if "title" not in result.columns:
            result["title"] = None
        if "creator_code" not in result.columns:
            result["creator_code"] = None

    result["updated_at"] = _utc_now()
    return result[
        [
            "island_code",
            "title",
            "creator_code",
            "latest_metric_timestamp",
            "peak_ccu",
            "unique_players",
            "plays",
            "minutes_played",
            "updated_at",
        ]
    ]


def build_top_islands_by_peak_ccu(
    activity: pd.DataFrame,
    *,
    top_n: Optional[int] = None,
) -> pd.DataFrame:
    """Rank islands by peak_ccu descending."""
    if activity is None or activity.empty or "peak_ccu" not in activity.columns:
        return _empty_frame(
            [
                "rank",
                "island_code",
                "title",
                "peak_ccu",
                "unique_players",
                "plays",
                "latest_metric_timestamp",
            ]
        )

    ranked = activity[activity["peak_ccu"].notna()].copy()
    ranked = ranked.sort_values("peak_ccu", ascending=False)
    if top_n is not None and top_n > 0:
        ranked = ranked.head(top_n)
    ranked.insert(0, "rank", range(1, len(ranked) + 1))
    return ranked[
        [
            "rank",
            "island_code",
            "title",
            "peak_ccu",
            "unique_players",
            "plays",
            "latest_metric_timestamp",
        ]
    ]


def build_island_activity_anomalies(
    metrics: pd.DataFrame,
    islands: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """Detect peakCCU spikes per island vs rolling history and previous point."""
    columns = [
        "island_code",
        "title",
        "metric_timestamp",
        "peak_ccu",
        "previous_peak_ccu",
        "rolling_avg_peak_ccu",
        "pct_change_from_previous",
        "deviation_from_rolling_avg",
        "anomaly_type",
        "severity",
        "detected_at",
    ]
    if metrics is None or metrics.empty:
        return _empty_frame(columns)

    work = metrics.copy()
    if "metric_name" in work.columns:
        work = work[work["metric_name"] == "peakCCU"]
    work["metric_timestamp"] = pd.to_datetime(work["metric_timestamp"], utc=True, errors="coerce")
    work = work.dropna(subset=["island_code", "metric_timestamp"])
    if work.empty:
        return _empty_frame(columns)

    title_map: Dict[str, Optional[str]] = {}
    if islands is not None and not islands.empty and "island_code" in islands.columns:
        meta = islands.drop_duplicates(subset=["island_code"])
        if "title" in meta.columns:
            title_map = dict(zip(meta["island_code"], meta["title"]))

    detected_at = _utc_now()
    rows: List[Dict[str, Any]] = []

    for island_code, group in work.groupby("island_code", sort=False):
        ordered = group.sort_values("metric_timestamp").reset_index(drop=True)
        values = ordered["metric_value"].tolist()
        timestamps = ordered["metric_timestamp"].tolist()

        for idx in range(1, len(ordered)):
            current = values[idx]
            if current is None or (isinstance(current, float) and pd.isna(current)):
                continue

            prev_slice = ordered.iloc[:idx]
            prev_valid = prev_slice[prev_slice["metric_value"].notna()]
            if prev_valid.empty:
                continue

            rolling_avg = float(prev_valid["metric_value"].mean())
            last_prev = float(prev_valid.iloc[-1]["metric_value"])
            previous_immediate = values[idx - 1]
            if isinstance(previous_immediate, float) and pd.isna(previous_immediate):
                previous_peak = last_prev
            else:
                previous_peak = float(previous_immediate)

            pct_change: Optional[float] = None
            if last_prev != 0:
                pct_change = (float(current) - last_prev) / last_prev
            elif current > 0:
                pct_change = 1.0

            deviation = float(current) - rolling_avg
            spike_vs_rolling = current >= rolling_avg * 1.5
            spike_vs_previous = pct_change is not None and pct_change >= 0.5

            if not (spike_vs_rolling or spike_vs_previous):
                continue

            types: List[str] = []
            if spike_vs_rolling:
                types.append("spike_vs_rolling_avg")
            if spike_vs_previous:
                types.append("spike_vs_previous")

            high = (pct_change is not None and pct_change >= 1.0) or current >= rolling_avg * 2
            severity = "high" if high else "medium"

            rows.append(
                {
                    "island_code": str(island_code),
                    "title": title_map.get(str(island_code)),
                    "metric_timestamp": timestamps[idx],
                    "peak_ccu": float(current),
                    "previous_peak_ccu": previous_peak,
                    "rolling_avg_peak_ccu": rolling_avg,
                    "pct_change_from_previous": pct_change,
                    "deviation_from_rolling_avg": deviation,
                    "anomaly_type": ",".join(types),
                    "severity": severity,
                    "detected_at": detected_at,
                }
            )

    if not rows:
        return _empty_frame(columns)

    result = pd.DataFrame(rows)
    result = result.sort_values("metric_timestamp", ascending=False)
    return result[columns]


def build_island_metric_hourly(metrics: pd.DataFrame) -> pd.DataFrame:
    """Hourly aggregates per island and metric (null-safe)."""
    if metrics is None or metrics.empty:
        return _empty_frame(
            [
                "island_code",
                "metric_name",
                "metric_hour",
                "avg_value",
                "min_value",
                "max_value",
                "sample_count",
            ]
        )

    work = metrics.copy()
    work["metric_timestamp"] = pd.to_datetime(work["metric_timestamp"], utc=True, errors="coerce")
    work = work.dropna(subset=["island_code", "metric_name", "metric_timestamp"])
    if work.empty:
        return _empty_frame(
            [
                "island_code",
                "metric_name",
                "metric_hour",
                "avg_value",
                "min_value",
                "max_value",
                "sample_count",
            ]
        )

    work["metric_hour"] = work["metric_timestamp"].dt.floor("h")
    grouped = (
        work.groupby(["island_code", "metric_name", "metric_hour"], dropna=False)
        .agg(
            avg_value=("metric_value", "mean"),
            min_value=("metric_value", "min"),
            max_value=("metric_value", "max"),
            sample_count=("island_code", "size"),
        )
        .reset_index()
    )
    grouped["metric_hour"] = grouped["metric_hour"].astype(str)
    return grouped


def build_shop_rarity_distribution(
    shop_items: pd.DataFrame,
    cosmetics: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """Count shop items by cosmetics rarity for latest snapshot."""
    if shop_items is None or shop_items.empty:
        return _empty_frame(
            ["snapshot_date", "rarity", "item_count", "share_pct", "updated_at"]
        )

    shop = shop_items.copy()
    if "snapshot_date" in shop.columns and shop["snapshot_date"].notna().any():
        latest = shop["snapshot_date"].max()
        shop = shop[shop["snapshot_date"] == latest]
    snapshot_date = shop["snapshot_date"].iloc[0] if "snapshot_date" in shop.columns else None

    if cosmetics is not None and not cosmetics.empty:
        cos = cosmetics[["cosmetic_id", "rarity"]].drop_duplicates(subset=["cosmetic_id"])
        merged = shop.merge(cos, left_on="dev_name", right_on="cosmetic_id", how="left")
    else:
        logger.warning("Cosmetics silver missing; shop rarity uses unknown rarity")
        merged = shop.copy()
        merged["rarity"] = None

    merged["rarity"] = merged["rarity"].fillna("unknown")
    counts = merged.groupby("rarity", as_index=False).size().rename(columns={"size": "item_count"})
    total = counts["item_count"].sum()
    counts["share_pct"] = (counts["item_count"] / total * 100.0) if total else 0.0
    counts["snapshot_date"] = snapshot_date
    counts["updated_at"] = _utc_now()
    return counts[["snapshot_date", "rarity", "item_count", "share_pct", "updated_at"]]


def build_source_health_summary(health_events: List[Dict[str, Any]]) -> pd.DataFrame:
    """Summarize bronze ingestion_status health events by source."""
    if not health_events:
        logger.warning("No ingestion_status bronze events; empty health summary")
        return _empty_frame(
            [
                "source_name",
                "last_success_at",
                "last_failure_at",
                "success_count",
                "failure_count",
                "latest_status",
            ]
        )

    rows: List[Dict[str, Any]] = []
    for raw in health_events:
        if not isinstance(raw, dict):
            continue
        source_name = raw.get("source") or raw.get("source_name") or raw.get("entity")
        status = str(raw.get("status") or "").lower()
        observed = raw.get("observed_at") or raw.get("ingested_at") or raw.get("event_time")
        if not source_name:
            continue
        rows.append(
            {
                "source_name": str(source_name),
                "status": status,
                "observed_at": observed,
            }
        )

    if not rows:
        return _empty_frame(
            [
                "source_name",
                "last_success_at",
                "last_failure_at",
                "success_count",
                "failure_count",
                "latest_status",
            ]
        )

    frame = pd.DataFrame(rows)
    frame["observed_at"] = pd.to_datetime(frame["observed_at"], utc=True, errors="coerce")

    summaries: List[Dict[str, Any]] = []
    for source_name, group in frame.groupby("source_name"):
        success = group[group["status"] == "success"]
        failure = group[group["status"] == "failed"]
        latest_row = group.sort_values("observed_at").iloc[-1]
        summaries.append(
            {
                "source_name": source_name,
                "last_success_at": success["observed_at"].max() if not success.empty else None,
                "last_failure_at": failure["observed_at"].max() if not failure.empty else None,
                "success_count": int(len(success)),
                "failure_count": int(len(failure)),
                "latest_status": latest_row["status"],
            }
        )
    return pd.DataFrame(summaries)


def parse_bronze_health_json(payload: bytes) -> Optional[Dict[str, Any]]:
    """Parse a bronze ingestion_status JSON object."""
    try:
        data = json.loads(payload.decode("utf-8"))
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None
