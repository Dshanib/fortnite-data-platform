"""DuckDB httpfs configuration for MinIO (S3-compatible) Gold reads."""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urlparse

import duckdb

from common.logging import get_logger

if TYPE_CHECKING:
    from config.settings import Settings

logger = get_logger(__name__)

GOLD_READ_MODE_DIRECT = "direct_minio"
GOLD_READ_MODE_LOCAL = "local_cache"
GOLD_READ_MODES = (GOLD_READ_MODE_DIRECT, GOLD_READ_MODE_LOCAL)


class DuckDBMinioConfigError(Exception):
    """Raised when httpfs or S3 settings cannot be applied."""


def normalize_s3_endpoint(minio_endpoint: str) -> str:
    """Strip scheme from MINIO_ENDPOINT for DuckDB s3_endpoint (host:port)."""
    raw = (minio_endpoint or "").strip()
    if "://" in raw:
        parsed = urlparse(raw)
        host = parsed.hostname or ""
        port = parsed.port
        if port:
            return f"{host}:{port}"
        if parsed.scheme == "https":
            return f"{host}:443" if host else host
        return f"{host}:9000" if host else host
    return raw.rstrip("/")


def get_gold_read_mode(settings: Settings, override: str | None = None) -> str:
    """Resolve active Gold read mode from override or settings."""
    mode = (override or settings.duckdb_gold_read_mode or GOLD_READ_MODE_LOCAL).strip().lower()
    if mode not in GOLD_READ_MODES:
        raise ValueError(
            f"Invalid Gold read mode '{mode}'. Use: {', '.join(GOLD_READ_MODES)}"
        )
    return mode


def configure_duckdb_minio(conn: duckdb.DuckDBPyConnection, settings: Settings) -> str:
    """
    Load httpfs and apply MinIO S3 settings. Returns normalized endpoint (no secrets).
    """
    try:
        conn.execute("INSTALL httpfs;")
        conn.execute("LOAD httpfs;")
    except duckdb.Error as exc:
        raise DuckDBMinioConfigError(
            "DuckDB httpfs extension could not be loaded. "
            "Ensure DuckDB is installed with extension support."
        ) from exc

    endpoint = normalize_s3_endpoint(settings.minio_endpoint)
    use_ssl = "true" if settings.minio_secure else "false"

    conn.execute(f"SET s3_endpoint='{endpoint}';")
    conn.execute(f"SET s3_access_key_id='{settings.minio_access_key}';")
    conn.execute(f"SET s3_secret_access_key='{settings.minio_secret_key}';")
    conn.execute(f"SET s3_use_ssl={use_ssl};")
    conn.execute("SET s3_url_style='path';")
    conn.execute("SET s3_region='us-east-1';")

    logger.info(
        "DuckDB S3 configured for MinIO endpoint=%s ssl=%s bucket=%s",
        endpoint,
        use_ssl,
        settings.minio_bucket,
    )
    return endpoint
