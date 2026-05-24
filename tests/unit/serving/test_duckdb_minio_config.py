"""DuckDB MinIO S3 configuration tests."""

from __future__ import annotations

from config.settings import get_settings
from serving.minio_duckdb import configure_duckdb_minio, normalize_s3_endpoint


def test_normalize_endpoint_strips_http() -> None:
    assert normalize_s3_endpoint("http://localhost:9000") == "localhost:9000"


def test_normalize_endpoint_strips_https() -> None:
    assert normalize_s3_endpoint("https://minio.example.com:9000") == "minio.example.com:9000"


def test_configure_duckdb_minio_sets_s3_no_secrets_in_logs(
    monkeypatch, caplog
) -> None:
    import duckdb

    settings = get_settings()
    conn = duckdb.connect(":memory:")
    endpoint = configure_duckdb_minio(conn, settings)

    assert endpoint == normalize_s3_endpoint(settings.minio_endpoint)
    row = conn.execute("SELECT current_setting('s3_url_style')").fetchone()
    assert row[0] == "path"

    logged = " ".join(r.getMessage() for r in caplog.records)
    assert settings.minio_secret_key not in logged
    assert settings.minio_access_key not in logged
    conn.close()
