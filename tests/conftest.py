"""Pytest fixtures and test environment defaults."""

from __future__ import annotations

import os

import pytest

from config.settings import get_settings


@pytest.fixture(autouse=True)
def _test_env(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """Provide valid configuration for unit tests."""
    get_settings.cache_clear()
    env = {
        "KAFKA_BOOTSTRAP_SERVERS": "localhost:9092",
        "KAFKA_TOPIC_CCU": "fortnite.raw.ccu",
        "KAFKA_TOPIC_SHOP": "fortnite.raw.shop",
        "KAFKA_TOPIC_COSMETICS": "fortnite.raw.cosmetics",
        "KAFKA_TOPIC_INGESTION_STATUS": "fortnite.ops.ingestion_status",
        "MINIO_PROFILE": "internal",
        "MINIO_ENDPOINT": "http://localhost:9000",
        "MINIO_ACCESS_KEY": "minioadmin",
        "MINIO_SECRET_KEY": "minioadmin",
        "MINIO_BUCKET": "fortnite-data",
        "MINIO_SECURE": "false",
        "TELEGRAM_BOT_TOKEN": "test-token",
        "DUCKDB_PATH": str(tmp_path / "test.duckdb"),
        "FORTNITE_API_BASE_URL": "https://fortnite-api.com",
        "FORTNITE_API_KEY": "",
        "CCU_SOURCE_URL": "https://example.com/status",
        "LOG_LEVEL": "WARNING",
        "REQUEST_TIMEOUT_SECONDS": "5",
        "REQUEST_RETRY_COUNT": "1",
    }
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    yield
    get_settings.cache_clear()
