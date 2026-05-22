"""Resolve Gold Parquet paths for DuckDB (direct MinIO or local cache)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from config.settings import Settings, get_settings
from serving.minio_duckdb import (
    GOLD_READ_MODE_DIRECT,
    GOLD_READ_MODE_LOCAL,
    get_gold_read_mode,
)

_GOLD_DATASETS = (
    "current_island_activity",
    "top_islands_by_peak_ccu",
    "island_metric_hourly",
    "island_activity_anomalies",
    "shop_rarity_distribution",
    "source_health_summary",
)

_ENV_BY_DATASET = {
    "current_island_activity": "GOLD_CURRENT_ISLAND_ACTIVITY_PATH",
    "top_islands_by_peak_ccu": "GOLD_TOP_ISLANDS_BY_PEAK_CCU_PATH",
    "island_metric_hourly": "GOLD_ISLAND_METRIC_HOURLY_PATH",
    "island_activity_anomalies": "GOLD_ISLAND_ACTIVITY_ANOMALIES_PATH",
    "shop_rarity_distribution": "GOLD_SHOP_RARITY_DISTRIBUTION_PATH",
    "source_health_summary": "GOLD_SOURCE_HEALTH_SUMMARY_PATH",
}


@dataclass(frozen=True)
class GoldDatasetPaths:
    """Resolved parquet globs per gold dataset."""

    current_island_activity: Optional[str]
    top_islands_by_peak_ccu: Optional[str]
    island_metric_hourly: Optional[str]
    island_activity_anomalies: Optional[str]
    shop_rarity_distribution: Optional[str]
    source_health_summary: Optional[str]
    read_mode: str = GOLD_READ_MODE_LOCAL

    def as_dict(self) -> Dict[str, Optional[str]]:
        return {
            "current_island_activity": self.current_island_activity,
            "top_islands_by_peak_ccu": self.top_islands_by_peak_ccu,
            "island_metric_hourly": self.island_metric_hourly,
            "island_activity_anomalies": self.island_activity_anomalies,
            "shop_rarity_distribution": self.shop_rarity_distribution,
            "source_health_summary": self.source_health_summary,
        }


def _to_local_parquet_glob(path: Path) -> Optional[str]:
    """Return a DuckDB-friendly glob for local parquet files."""
    if path.is_file() and path.suffix == ".parquet":
        return str(path.resolve()).replace("\\", "/")
    if path.is_dir():
        files = list(path.rglob("*.parquet"))
        if not files:
            return None
        return str((path / "**" / "*.parquet").resolve()).replace("\\", "/")
    return None


def _resolve_local_dataset_path(settings: Settings, dataset: str) -> Optional[str]:
    env_name = _ENV_BY_DATASET[dataset]
    override = os.getenv(env_name, "").strip()
    if override:
        return _to_local_parquet_glob(Path(override))
    default_dir = Path(settings.gold_data_root) / dataset
    return _to_local_parquet_glob(default_dir)


def _resolve_direct_minio_dataset_path(settings: Settings, dataset: str) -> str:
    env_name = _ENV_BY_DATASET[dataset]
    override = os.getenv(env_name, "").strip()
    if override:
        return override.replace("\\", "/")
    bucket = settings.minio_bucket
    return f"s3://{bucket}/gold/{dataset}/**/*.parquet"


def resolve_gold_paths(
    settings: Optional[Settings] = None,
    *,
    mode: Optional[str] = None,
) -> GoldDatasetPaths:
    """Resolve gold parquet globs for direct MinIO or local cache."""
    settings = settings or get_settings()
    read_mode = get_gold_read_mode(settings, mode)

    if read_mode == GOLD_READ_MODE_DIRECT:
        resolved = {
            name: _resolve_direct_minio_dataset_path(settings, name) for name in _GOLD_DATASETS
        }
    else:
        resolved = {
            name: _resolve_local_dataset_path(settings, name) for name in _GOLD_DATASETS
        }

    return GoldDatasetPaths(**resolved, read_mode=read_mode)


def list_parquet_files(glob_or_path: Optional[str]) -> List[Path]:
    """Expand a local glob string to concrete parquet file paths."""
    if not glob_or_path or glob_or_path.startswith("s3://"):
        return []
    path = Path(glob_or_path)
    if path.is_file():
        return [path]
    if "**" in glob_or_path:
        base = Path(glob_or_path.split("**")[0])
        return sorted(base.rglob("*.parquet"))
    if path.is_dir():
        return sorted(path.rglob("*.parquet"))
    return []
