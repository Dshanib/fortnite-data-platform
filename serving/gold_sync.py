"""
Sync Gold Parquet from MinIO to local cache for DuckDB serving.

Used when DUCKDB_GOLD_READ_MODE=local_cache or as fallback when direct_minio
view setup fails. Not required for direct_minio mode.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse

from minio import Minio

from common.logging import get_logger
from config.settings import Settings, get_settings
from serving.gold_paths import _GOLD_DATASETS

logger = get_logger(__name__)


def _minio_client(settings: Settings) -> Minio:
    parsed = urlparse(settings.minio_endpoint)
    host = parsed.hostname or ""
    port = parsed.port or (443 if settings.minio_secure else 9000)
    return Minio(
        f"{host}:{port}",
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


def sync_gold_from_minio(
    settings: Optional[Settings] = None,
    *,
    datasets: Optional[List[str]] = None,
) -> int:
    """
    Download gold/{dataset}/ parquet objects into GOLD_DATA_ROOT/{dataset}/.
    Returns number of files downloaded.
    """
    settings = settings or get_settings()
    client = _minio_client(settings)
    bucket = settings.minio_bucket
    root = Path(settings.gold_data_root)
    root.mkdir(parents=True, exist_ok=True)

    targets = datasets or list(_GOLD_DATASETS)
    downloaded = 0

    for dataset in targets:
        prefix = f"gold/{dataset}/"
        out_dir = root / dataset
        for obj in client.list_objects(bucket, prefix=prefix, recursive=True):
            if not obj.object_name.endswith(".parquet"):
                continue
            rel = obj.object_name[len(prefix) :]
            local_path = out_dir / rel
            local_path.parent.mkdir(parents=True, exist_ok=True)
            client.fget_object(bucket, obj.object_name, str(local_path))
            downloaded += 1
            logger.info("Synced %s -> %s", obj.object_name, local_path)

    return downloaded
