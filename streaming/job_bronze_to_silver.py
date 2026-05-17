"""Batch job: read Bronze JSON from MinIO, write Silver Parquet."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from pyspark.sql import DataFrame, SparkSession

from common.logging import configure_logging, get_logger
from config.settings import Settings, get_settings
from streaming.schemas import (
    COSMETICS_SCHEMA,
    ISLAND_METRICS_SCHEMA,
    ISLANDS_SCHEMA,
    SHOP_ITEMS_SCHEMA,
)
from streaming.spark_session import bronze_path, silver_path
from streaming.transformations import (
    transform_cosmetics_events,
    transform_island_metrics_events,
    transform_islands_events,
    transform_shop_events,
)

logger = get_logger(__name__)


@dataclass
class DatasetResult:
    """Summary for one bronze→silver dataset."""

    source: str
    silver_dataset: str
    input_count: int
    output_count: int
    target_path: str
    status: str


def _read_bronze_events(spark: SparkSession, path: str) -> Optional[DataFrame]:
    try:
        return spark.read.option("multiLine", True).json(path)
    except Exception as exc:
        logger.warning("Failed to read bronze path=%s: %s", path, exc)
        return None


def _dataframe_to_events(raw_df: DataFrame) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    for row in raw_df.collect():
        event = row.asDict(recursive=True)
        if event:
            events.append(event)
    return events


def _write_silver(
    spark: SparkSession,
    rows: List[Dict[str, Any]],
    schema: Any,
    output_uri: str,
    *,
    partition_by: Optional[List[str]] = None,
) -> int:
    if not rows:
        return 0
    silver_df = spark.createDataFrame(rows, schema=schema)
    writer = silver_df.write.mode("overwrite").format("parquet")
    if partition_by:
        writer = writer.partitionBy(*partition_by)
    writer.save(output_uri)
    return silver_df.count()


def process_dataset(
    spark: SparkSession,
    settings: Settings,
    *,
    bronze_source: str,
    silver_dataset: str,
    transform_fn: Callable[[List[Dict[str, Any]]], List[Dict[str, Any]]],
    schema: Any,
    partition_by: Optional[List[str]] = None,
) -> DatasetResult:
    """Process one bronze source into a silver Parquet dataset."""
    input_uri = bronze_path(settings, bronze_source)
    output_uri = silver_path(settings, silver_dataset)

    raw_df = _read_bronze_events(spark, input_uri)
    if raw_df is None:
        return DatasetResult(
            source=bronze_source,
            silver_dataset=silver_dataset,
            input_count=0,
            output_count=0,
            target_path=output_uri,
            status="skipped",
        )

    input_count = raw_df.count()
    if input_count == 0:
        logger.warning("No bronze files for source=%s", bronze_source)
        return DatasetResult(
            source=bronze_source,
            silver_dataset=silver_dataset,
            input_count=0,
            output_count=0,
            target_path=output_uri,
            status="empty",
        )

    events = _dataframe_to_events(raw_df)
    rows = transform_fn(events)
    output_count = _write_silver(
        spark, rows, schema, output_uri, partition_by=partition_by
    )

    status = "success" if output_count > 0 else "no_rows"
    logger.info(
        "Silver write source=%s dataset=%s input=%s output=%s",
        bronze_source,
        silver_dataset,
        input_count,
        output_count,
    )
    return DatasetResult(
        source=bronze_source,
        silver_dataset=silver_dataset,
        input_count=input_count,
        output_count=output_count,
        target_path=output_uri,
        status=status,
    )


def run_job(
    spark: SparkSession,
    settings: Optional[Settings] = None,
    *,
    sources: Optional[List[str]] = None,
) -> List[DatasetResult]:
    """Run bronze→silver transformations (all sources, or a subset)."""
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    allowed = {s.strip() for s in sources} if sources else None

    tasks = [
        ("shop", "shop_items", transform_shop_events, SHOP_ITEMS_SCHEMA, ["snapshot_date"]),
        ("cosmetics", "cosmetics", transform_cosmetics_events, COSMETICS_SCHEMA, None),
        ("islands", "islands", transform_islands_events, ISLANDS_SCHEMA, None),
        (
            "island_metrics",
            "island_metrics",
            transform_island_metrics_events,
            ISLAND_METRICS_SCHEMA,
            ["metric_date"],
        ),
    ]

    results: List[DatasetResult] = []
    for bronze_source, silver_dataset, transform_fn, schema, partition_by in tasks:
        if allowed is not None and bronze_source not in allowed:
            continue
        results.append(
            process_dataset(
                spark,
                settings,
                bronze_source=bronze_source,
                silver_dataset=silver_dataset,
                transform_fn=transform_fn,
                schema=schema,
                partition_by=partition_by,
            )
        )
    return results
