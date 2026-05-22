"""Silver → Gold using MinIO + PyArrow (fast local dev, no Spark JVM)."""

from __future__ import annotations

import json
import os
import tempfile
from io import BytesIO
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import pandas as pd
from minio import Minio

from common.exceptions import StorageError
from common.logging import configure_logging, get_logger
from config.settings import Settings, get_settings
from storage.parquet_names import dataset_parquet_filename
from streaming.gold_transformations import (
    build_current_island_activity,
    build_island_activity_anomalies,
    build_island_metric_hourly,
    build_shop_rarity_distribution,
    build_source_health_summary,
    build_top_islands_by_peak_ccu,
    parse_bronze_health_json,
)
from streaming.job_silver_to_gold import GoldDatasetResult

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


def _read_parquet_prefix(client: Minio, bucket: str, prefix: str) -> Optional[pd.DataFrame]:
    frames: List[pd.DataFrame] = []
    for obj in client.list_objects(bucket, prefix=prefix, recursive=True):
        if not obj.object_name.endswith(".parquet"):
            continue
        response = client.get_object(bucket, obj.object_name)
        try:
            frames.append(pd.read_parquet(BytesIO(response.read())))
        finally:
            response.close()
            response.release_conn()
    if not frames:
        return None
    return pd.concat(frames, ignore_index=True)


def _load_bronze_health(client: Minio, bucket: str) -> List[Dict[str, Any]]:
    prefix = "bronze/source=ingestion_status/"
    events: List[Dict[str, Any]] = []
    for obj in client.list_objects(bucket, prefix=prefix, recursive=True):
        if not obj.object_name.endswith(".json"):
            continue
        response = client.get_object(bucket, obj.object_name)
        try:
            parsed = parse_bronze_health_json(response.read())
            if parsed:
                events.append(parsed)
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


def _write_gold_local(
    client: Minio,
    settings: Settings,
    frame: pd.DataFrame,
    dataset: str,
) -> int:
    if frame is None or frame.empty:
        return 0
    prefix = f"gold/{dataset}/"
    target = f"s3a://{settings.minio_bucket}/{prefix}"
    _clear_prefix(client, settings.minio_bucket, prefix)
    with tempfile.TemporaryDirectory() as tmp:
        frame.to_parquet(
            os.path.join(tmp, dataset_parquet_filename(dataset)),
            engine="pyarrow",
            index=False,
        )
        _upload_tree(client, settings.minio_bucket, tmp, prefix)
    return len(frame)


def run_job_local(
    settings: Optional[Settings] = None,
    *,
    top_islands_n: Optional[int] = None,
) -> List[GoldDatasetResult]:
    """Build gold datasets without Spark."""
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    client = _minio_client(settings)
    bucket = settings.minio_bucket
    results: List[GoldDatasetResult] = []

    metrics = _read_parquet_prefix(client, bucket, "silver/island_metrics/")
    if metrics is None or metrics.empty:
        raise StorageError(
            "Required silver/island_metrics is missing. "
            "Run: python scripts/run_bronze_to_silver.py --engine python"
        )
    metrics_input = len(metrics)

    islands = _read_parquet_prefix(client, bucket, "silver/islands/")
    if islands is None or islands.empty:
        logger.warning("silver/islands missing; island titles may be empty")

    activity = build_current_island_activity(metrics, islands)
    activity_uri = f"s3a://{bucket}/gold/current_island_activity/"
    activity_out = _write_gold_local(client, settings, activity, "current_island_activity")
    results.append(
        GoldDatasetResult(
            name="current_island_activity",
            input_count=metrics_input,
            output_count=activity_out,
            target_path=activity_uri,
            status="success" if activity_out > 0 else "empty",
        )
    )

    top = build_top_islands_by_peak_ccu(activity, top_n=top_islands_n)
    top_uri = f"s3a://{bucket}/gold/top_islands_by_peak_ccu/"
    top_out = _write_gold_local(client, settings, top, "top_islands_by_peak_ccu")
    results.append(
        GoldDatasetResult(
            name="top_islands_by_peak_ccu",
            input_count=activity_out,
            output_count=top_out,
            target_path=top_uri,
            status="success" if top_out > 0 else "empty",
        )
    )

    hourly = build_island_metric_hourly(metrics)
    hourly_uri = f"s3a://{bucket}/gold/island_metric_hourly/"
    hourly_out = _write_gold_local(client, settings, hourly, "island_metric_hourly")
    results.append(
        GoldDatasetResult(
            name="island_metric_hourly",
            input_count=metrics_input,
            output_count=hourly_out,
            target_path=hourly_uri,
            status="success" if hourly_out > 0 else "empty",
        )
    )

    anomalies = build_island_activity_anomalies(metrics, islands)
    anomalies_uri = f"s3a://{bucket}/gold/island_activity_anomalies/"
    anomalies_out = _write_gold_local(client, settings, anomalies, "island_activity_anomalies")
    results.append(
        GoldDatasetResult(
            name="island_activity_anomalies",
            input_count=metrics_input,
            output_count=anomalies_out,
            target_path=anomalies_uri,
            status="success" if anomalies_out > 0 else "empty",
        )
    )

    shop = _read_parquet_prefix(client, bucket, "silver/shop_items/")
    cosmetics = _read_parquet_prefix(client, bucket, "silver/cosmetics/")
    if cosmetics is None or cosmetics.empty:
        logger.warning("silver/cosmetics missing; shop rarity may show unknown")
    rarity = build_shop_rarity_distribution(shop, cosmetics)
    rarity_uri = f"s3a://{bucket}/gold/shop_rarity_distribution/"
    shop_input = len(shop) if shop is not None else 0
    rarity_out = _write_gold_local(client, settings, rarity, "shop_rarity_distribution")
    results.append(
        GoldDatasetResult(
            name="shop_rarity_distribution",
            input_count=shop_input,
            output_count=rarity_out,
            target_path=rarity_uri,
            status="success" if rarity_out > 0 else "empty",
        )
    )

    health_events = _load_bronze_health(client, bucket)
    health = build_source_health_summary(health_events)
    health_uri = f"s3a://{bucket}/gold/source_health_summary/"
    health_out = _write_gold_local(client, settings, health, "source_health_summary")
    results.append(
        GoldDatasetResult(
            name="source_health_summary",
            input_count=len(health_events),
            output_count=health_out,
            target_path=health_uri,
            status="success" if health_out > 0 else "empty",
        )
    )

    return results
