"""Resolve Silver Parquet paths for DuckDB shop/cosmetics views."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from config.settings import Settings, get_settings
from serving.gold_paths import _to_local_parquet_glob
from serving.minio_duckdb import GOLD_READ_MODE_DIRECT, get_gold_read_mode

_SILVER_DATASETS = ("shop_items", "cosmetics")


@dataclass(frozen=True)
class SilverDatasetPaths:
    shop_items: Optional[str]
    cosmetics: Optional[str]
    read_mode: str

    def as_dict(self) -> Dict[str, Optional[str]]:
        return {"shop_items": self.shop_items, "cosmetics": self.cosmetics}


def _resolve_silver_local(settings: Settings, dataset: str) -> Optional[str]:
    env_name = f"SILVER_{dataset.upper()}_PATH"
    override = os.getenv(env_name, "").strip()
    if override:
        return _to_local_parquet_glob(Path(override))
    root = os.getenv("SILVER_DATA_ROOT", "").strip()
    if root:
        return _to_local_parquet_glob(Path(root) / dataset)
    base = Path(settings.gold_data_root).parent
    if base.name == "gold":
        base = base.parent
    return _to_local_parquet_glob(base / "silver" / dataset)


def resolve_silver_paths(
    settings: Optional[Settings] = None,
    *,
    mode: Optional[str] = None,
) -> SilverDatasetPaths:
    settings = settings or get_settings()
    read_mode = get_gold_read_mode(settings, mode)
    bucket = settings.minio_bucket

    if read_mode == GOLD_READ_MODE_DIRECT:
        resolved = {
            name: f"s3://{bucket}/silver/{name}/**/*.parquet" for name in _SILVER_DATASETS
        }
    else:
        resolved = {name: _resolve_silver_local(settings, name) for name in _SILVER_DATASETS}
    return SilverDatasetPaths(
        shop_items=resolved["shop_items"],
        cosmetics=resolved["cosmetics"],
        read_mode=read_mode,
    )
