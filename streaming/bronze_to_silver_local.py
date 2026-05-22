"""Bronze → Silver using MinIO client + PyArrow (fast local dev, no Spark JVM)."""

from __future__ import annotations

import json
import os
import tempfile
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlparse

import pandas as pd
from minio import Minio

from common.logging import configure_logging, get_logger
from config.settings import Settings, get_settings
from storage.parquet_names import (
    dataset_parquet_filename,
    dataset_partition_basename_template,
)
from streaming.job_bronze_to_silver import DatasetResult
from streaming.transformations import (
    transform_cosmetics_events,
    transform_island_metrics_events,
    transform_islands_events,
    transform_shop_events,
)

logger = get_logger(__name__)

TASKS = [
    ("shop", "shop_items", transform_shop_events, ["snapshot_date"]),
    ("cosmetics", "cosmetics", transform_cosmetics_events, None),
    ("islands", "islands", transform_islands_events, None),
    ("island_metrics", "island_metrics", transform_island_metrics_events, ["metric_date"]),
]


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


def _load_bronze_events(client: Minio, bucket: str, source: str) -> List[Dict[str, Any]]:
    prefix = f"bronze/source={source}/"
    events: List[Dict[str, Any]] = []
    for obj in client.list_objects(bucket, prefix=prefix, recursive=True):
        if not obj.object_name.endswith(".json"):
            continue
        response = client.get_object(bucket, obj.object_name)
        try:
            payload = json.loads(response.read().decode("utf-8"))
            if isinstance(payload, dict):
                events.append(payload)
        except json.JSONDecodeError as exc:
            logger.warning("Invalid bronze JSON key=%s: %s", obj.object_name, exc)
        finally:
            response.close()
            response.release_conn()
    return events


def _clear_prefix(client: Minio, bucket: str, prefix: str) -> None:
    for obj in client.list_objects(bucket, prefix=prefix, recursive=True):
        client.remove_object(bucket, obj.object_name)


def _upload_tree(client: Minio, bucket: str, local_dir: str, remote_prefix: str) -> int:
    uploaded = 0
    for root, _, files in os.walk(local_dir):
        for name in files:
            local_path = os.path.join(root, name)
            rel = os.path.relpath(local_path, local_dir).replace("\\", "/")
            key = f"{remote_prefix.rstrip('/')}/{rel}"
            client.fput_object(bucket, key, local_path)
            uploaded += 1
    return uploaded


def process_dataset_local(
    settings: Settings,
    client: Minio,
    *,
    bronze_source: str,
    silver_dataset: str,
    transform_fn: Callable[[List[Dict[str, Any]]], List[Dict[str, Any]]],
    partition_by: Optional[List[str]] = None,
) -> DatasetResult:
    """Read bronze JSON from MinIO, write silver Parquet back to MinIO."""
    bucket = settings.minio_bucket
    output_prefix = f"silver/{silver_dataset}/"
    target_path = f"s3a://{bucket}/{output_prefix}"

    events = _load_bronze_events(client, bucket, bronze_source)
    input_count = len(events)
    if input_count == 0:
        return DatasetResult(
            source=bronze_source,
            silver_dataset=silver_dataset,
            input_count=0,
            output_count=0,
            target_path=target_path,
            status="empty",
        )

    rows = transform_fn(events)
    if not rows:
        return DatasetResult(
            source=bronze_source,
            silver_dataset=silver_dataset,
            input_count=input_count,
            output_count=0,
            target_path=target_path,
            status="no_rows",
        )

    frame = pd.DataFrame(rows)
    if "processed_at" in frame.columns:
        frame["processed_at"] = pd.to_datetime(frame["processed_at"], utc=True)

    _clear_prefix(client, bucket, output_prefix)
    with tempfile.TemporaryDirectory() as tmp:
        if partition_by:
            frame.to_parquet(
                tmp,
                engine="pyarrow",
                index=False,
                partition_cols=partition_by,
                basename_template=dataset_partition_basename_template(silver_dataset),
            )
        else:
            os.makedirs(tmp, exist_ok=True)
            frame.to_parquet(
                os.path.join(tmp, dataset_parquet_filename(silver_dataset)),
                engine="pyarrow",
                index=False,
            )
        files_uploaded = _upload_tree(client, bucket, tmp, output_prefix)

    status = "success" if files_uploaded > 0 else "no_rows"
    return DatasetResult(
        source=bronze_source,
        silver_dataset=silver_dataset,
        input_count=input_count,
        output_count=len(rows),
        target_path=target_path,
        status=status,
    )


def run_job_local(
    settings: Optional[Settings] = None,
    *,
    sources: Optional[List[str]] = None,
) -> List[DatasetResult]:
    """Run bronze→silver without Spark (recommended for local Windows dev)."""
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    allowed = {s.strip() for s in sources} if sources else None
    client = _minio_client(settings)

    results: List[DatasetResult] = []
    for bronze_source, silver_dataset, transform_fn, partition_by in TASKS:
        if allowed is not None and bronze_source not in allowed:
            continue
        logger.info("Processing source=%s → silver/%s", bronze_source, silver_dataset)
        results.append(
            process_dataset_local(
                settings,
                client,
                bronze_source=bronze_source,
                silver_dataset=silver_dataset,
                transform_fn=transform_fn,
                partition_by=partition_by,
            )
        )
    return results
