"""Spark schemas for Silver datasets."""

from __future__ import annotations

from pyspark.sql.types import (
    BooleanType,
    DoubleType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

SHOP_ITEMS_SCHEMA = StructType(
    [
        StructField("snapshot_date", StringType(), True),
        StructField("offer_id", StringType(), True),
        StructField("dev_name", StringType(), True),
        StructField("regular_price", DoubleType(), True),
        StructField("final_price", DoubleType(), True),
        StructField("giftable", BooleanType(), True),
        StructField("refundable", BooleanType(), True),
        StructField("in_date", StringType(), True),
        StructField("out_date", StringType(), True),
        StructField("layout_id", StringType(), True),
        StructField("source_event_id", StringType(), True),
        StructField("ingested_at", StringType(), True),
        StructField("processed_at", TimestampType(), True),
    ]
)

COSMETICS_SCHEMA = StructType(
    [
        StructField("cosmetic_id", StringType(), True),
        StructField("name", StringType(), True),
        StructField("description", StringType(), True),
        StructField("rarity", StringType(), True),
        StructField("type", StringType(), True),
        StructField("set_name", StringType(), True),
        StructField("introduction_text", StringType(), True),
        StructField("source_event_id", StringType(), True),
        StructField("ingested_at", StringType(), True),
        StructField("processed_at", TimestampType(), True),
    ]
)

ISLANDS_SCHEMA = StructType(
    [
        StructField("island_code", StringType(), True),
        StructField("title", StringType(), True),
        StructField("creator_code", StringType(), True),
        StructField("display_name", StringType(), True),
        StructField("category", StringType(), True),
        StructField("created_in", StringType(), True),
        StructField("tags", StringType(), True),
        StructField("source_event_id", StringType(), True),
        StructField("ingested_at", StringType(), True),
        StructField("processed_at", TimestampType(), True),
    ]
)

ISLAND_METRICS_SCHEMA = StructType(
    [
        StructField("island_code", StringType(), True),
        StructField("interval_type", StringType(), True),
        StructField("metric_name", StringType(), True),
        StructField("metric_timestamp", StringType(), True),
        StructField("metric_date", StringType(), True),
        StructField("metric_value", DoubleType(), True),
        StructField("source_event_id", StringType(), True),
        StructField("ingested_at", StringType(), True),
        StructField("processed_at", TimestampType(), True),
    ]
)
