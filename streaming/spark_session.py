"""Spark session factory with MinIO S3A configuration."""

from __future__ import annotations

from typing import Optional
from urllib.parse import urlparse

from pyspark.sql import SparkSession

from common.validators import validate_minio_profile
from config.settings import Settings, get_settings


def parse_s3a_endpoint(minio_endpoint: str, minio_secure: bool) -> tuple[str, bool]:
    """Return S3A endpoint host:port and SSL flag from MINIO_ENDPOINT."""
    if "://" in minio_endpoint:
        parsed = urlparse(minio_endpoint)
        host = parsed.hostname or ""
        port = parsed.port or (443 if parsed.scheme == "https" else 9000)
        use_ssl = parsed.scheme == "https"
    else:
        host = minio_endpoint.split(":")[0]
        port = (
            int(minio_endpoint.split(":")[1])
            if ":" in minio_endpoint
            else (443 if minio_secure else 9000)
        )
        use_ssl = minio_secure
    if not host:
        raise ValueError(f"Invalid MINIO_ENDPOINT: {minio_endpoint}")
    return f"{host}:{port}", use_ssl


def bronze_path(settings: Settings, source: str) -> str:
    """S3A URI for a bronze source prefix."""
    return f"s3a://{settings.minio_bucket}/bronze/source={source}/"


def silver_path(settings: Settings, dataset: str) -> str:
    """S3A URI for a silver dataset prefix."""
    return f"s3a://{settings.minio_bucket}/silver/{dataset}/"


def gold_path(settings: Settings, dataset: str) -> str:
    """S3A URI for a gold dataset prefix."""
    return f"s3a://{settings.minio_bucket}/gold/{dataset}/"


def build_spark_session(
    settings: Optional[Settings] = None,
    *,
    app_name: str = "fortnite-bronze-to-silver",
) -> SparkSession:
    """Create a local Spark session configured for MinIO (internal or external profile)."""
    settings = settings or get_settings()
    validate_minio_profile(settings.minio_profile)

    endpoint, use_ssl = parse_s3a_endpoint(
        settings.minio_endpoint, settings.minio_secure
    )
    packages = (
        "org.apache.hadoop:hadoop-aws:3.3.4,"
        "com.amazonaws:aws-java-sdk-bundle:1.12.262"
    )

    builder = (
        SparkSession.builder.appName(app_name)
        .master("local[*]")
        .config("spark.hadoop.fs.s3a.endpoint", endpoint)
        .config("spark.hadoop.fs.s3a.access.key", settings.minio_access_key)
        .config("spark.hadoop.fs.s3a.secret.key", settings.minio_secret_key)
        .config("spark.hadoop.fs.s3a.path.style.access", "true")
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled", str(use_ssl).lower())
        .config("spark.hadoop.fs.s3a.aws.credentials.provider", "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider")
        .config("spark.jars.packages", packages)
        .config("spark.sql.sources.partitionOverwriteMode", "dynamic")
        .config("spark.sql.parquet.compression.codec", "snappy")
    )

    return builder.getOrCreate()
