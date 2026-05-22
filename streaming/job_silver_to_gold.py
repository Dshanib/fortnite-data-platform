"""Batch job: read Silver Parquet from MinIO, write Gold Parquet (PySpark)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from pyspark.sql import DataFrame, SparkSession

from common.exceptions import StorageError
from common.logging import configure_logging, get_logger
from config.settings import Settings, get_settings
from streaming.gold_transformations import (
    build_current_island_activity,
    build_island_activity_anomalies,
    build_island_metric_hourly,
    build_shop_rarity_distribution,
    build_source_health_summary,
    build_top_islands_by_peak_ccu,
)
from streaming.spark_session import bronze_path, gold_path, silver_path

logger = get_logger(__name__)


@dataclass
class GoldDatasetResult:
    """Summary for one gold dataset write."""

    name: str
    input_count: int
    output_count: int
    target_path: str
    status: str


def _read_silver_parquet(spark: SparkSession, path: str) -> Optional[DataFrame]:
    try:
        frame = spark.read.parquet(path)
        if frame.rdd.isEmpty():
            return None
        return frame
    except Exception as exc:
        logger.warning("Silver read failed path=%s: %s", path, exc)
        return None


def _read_bronze_health(spark: SparkSession, settings: Settings) -> List[dict]:
    path = bronze_path(settings, "ingestion_status")
    try:
        raw = spark.read.option("multiLine", True).json(path)
        if raw.rdd.isEmpty():
            return []
        return [row.asDict(recursive=True) for row in raw.collect()]
    except Exception as exc:
        logger.warning("Bronze ingestion_status read failed: %s", exc)
        return []


def _write_gold(
    spark: SparkSession,
    pandas_frame,
    output_uri: str,
) -> int:
    if pandas_frame is None or pandas_frame.empty:
        return 0
    gold_df = spark.createDataFrame(pandas_frame)
    gold_df.write.mode("overwrite").format("parquet").save(output_uri)
    return gold_df.count()


def run_job(
    spark: SparkSession,
    settings: Optional[Settings] = None,
    *,
    top_islands_n: Optional[int] = None,
) -> List[GoldDatasetResult]:
    """Build all gold datasets from silver (and bronze health) inputs."""
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    results: List[GoldDatasetResult] = []

    metrics_spark = _read_silver_parquet(
        spark, silver_path(settings, "island_metrics")
    )
    if metrics_spark is None:
        raise StorageError(
            "Required silver/island_metrics is missing. "
            "Run bronze→silver for island_metrics first."
        )

    metrics_pdf = metrics_spark.toPandas()
    metrics_input = len(metrics_pdf)

    islands_spark = _read_silver_parquet(spark, silver_path(settings, "islands"))
    islands_pdf = islands_spark.toPandas() if islands_spark is not None else None
    if islands_pdf is None or islands_pdf.empty:
        logger.warning("silver/islands missing; island titles may be empty")

    activity_pdf = build_current_island_activity(metrics_pdf, islands_pdf)
    activity_uri = gold_path(settings, "current_island_activity")
    activity_out = _write_gold(spark, activity_pdf, activity_uri)
    results.append(
        GoldDatasetResult(
            name="current_island_activity",
            input_count=metrics_input,
            output_count=activity_out,
            target_path=activity_uri,
            status="success" if activity_out > 0 else "empty",
        )
    )

    top_pdf = build_top_islands_by_peak_ccu(activity_pdf, top_n=top_islands_n)
    top_uri = gold_path(settings, "top_islands_by_peak_ccu")
    top_out = _write_gold(spark, top_pdf, top_uri)
    results.append(
        GoldDatasetResult(
            name="top_islands_by_peak_ccu",
            input_count=activity_out,
            output_count=top_out,
            target_path=top_uri,
            status="success" if top_out > 0 else "empty",
        )
    )

    hourly_pdf = build_island_metric_hourly(metrics_pdf)
    hourly_uri = gold_path(settings, "island_metric_hourly")
    hourly_out = _write_gold(spark, hourly_pdf, hourly_uri)
    results.append(
        GoldDatasetResult(
            name="island_metric_hourly",
            input_count=metrics_input,
            output_count=hourly_out,
            target_path=hourly_uri,
            status="success" if hourly_out > 0 else "empty",
        )
    )

    anomalies_pdf = build_island_activity_anomalies(metrics_pdf, islands_pdf)
    anomalies_uri = gold_path(settings, "island_activity_anomalies")
    anomalies_out = _write_gold(spark, anomalies_pdf, anomalies_uri)
    results.append(
        GoldDatasetResult(
            name="island_activity_anomalies",
            input_count=metrics_input,
            output_count=anomalies_out,
            target_path=anomalies_uri,
            status="success" if anomalies_out > 0 else "empty",
        )
    )

    shop_spark = _read_silver_parquet(spark, silver_path(settings, "shop_items"))
    shop_pdf = shop_spark.toPandas() if shop_spark is not None else None
    cosmetics_spark = _read_silver_parquet(spark, silver_path(settings, "cosmetics"))
    cosmetics_pdf = cosmetics_spark.toPandas() if cosmetics_spark is not None else None
    if cosmetics_pdf is None or cosmetics_pdf.empty:
        logger.warning("silver/cosmetics missing; shop rarity may show unknown")

    rarity_pdf = build_shop_rarity_distribution(shop_pdf, cosmetics_pdf)
    rarity_uri = gold_path(settings, "shop_rarity_distribution")
    shop_input = len(shop_pdf) if shop_pdf is not None else 0
    rarity_out = _write_gold(spark, rarity_pdf, rarity_uri)
    results.append(
        GoldDatasetResult(
            name="shop_rarity_distribution",
            input_count=shop_input,
            output_count=rarity_out,
            target_path=rarity_uri,
            status="success" if rarity_out > 0 else "empty",
        )
    )

    health_events = _read_bronze_health(spark, settings)
    health_pdf = build_source_health_summary(health_events)
    health_uri = gold_path(settings, "source_health_summary")
    health_out = _write_gold(spark, health_pdf, health_uri)
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
