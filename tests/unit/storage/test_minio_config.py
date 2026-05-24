"""MinIO configuration and client unit tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from common.exceptions import ValidationError
from common.validators import validate_minio_config, validate_minio_profile
from config.settings import get_settings
from storage.minio_client import MinioStorageClient
from storage.writers import write_raw_event_to_bronze


def test_validate_minio_profile() -> None:
    validate_minio_profile("internal")
    validate_minio_profile("external")
    with pytest.raises(ValidationError):
        validate_minio_profile("invalid")


def test_storage_settings_valid() -> None:
    settings = get_settings()
    validate_minio_config(
        {
            "minio_profile": settings.minio_profile,
            "minio_endpoint": settings.minio_endpoint,
            "minio_access_key": settings.minio_access_key,
            "minio_secret_key": settings.minio_secret_key,
            "minio_bucket": settings.minio_bucket,
            "minio_secure": settings.minio_secure,
        }
    )


def test_minio_config_invalid_endpoint() -> None:
    with pytest.raises(ValidationError):
        validate_minio_config(
            {
                "minio_profile": "internal",
                "minio_endpoint": "",
                "minio_access_key": "a",
                "minio_secret_key": "b",
                "minio_bucket": "c",
                "minio_secure": False,
            }
        )


def test_minio_client_uses_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = get_settings()
    client = MinioStorageClient(settings)
    assert client.profile == settings.minio_profile
    assert client.endpoint == settings.minio_endpoint
    assert client.bucket == settings.minio_bucket


def test_write_raw_event_to_bronze_mocked() -> None:
    settings = get_settings()
    mock_client = MagicMock()
    mock_client.ensure_bucket.return_value = None
    mock_client.put_bytes.return_value = None

    event = {
        "event_id": "evt-1",
        "event_type": "shop",
        "event_time": "2026-05-17T12:00:00+00:00",
        "ingested_at": "2026-05-17T12:00:01+00:00",
        "payload": {"status": 200},
    }
    key = write_raw_event_to_bronze(
        event,
        topic="fortnite.raw.shop",
        settings=settings,
        client=mock_client,
    )
    assert key.startswith("bronze/source=shop/event_date=2026-05-17/raw_shop_")
    mock_client.put_bytes.assert_called_once()
