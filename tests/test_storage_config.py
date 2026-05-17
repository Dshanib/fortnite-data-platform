"""Storage configuration validation tests."""

from __future__ import annotations

import pytest

from common.exceptions import ValidationError
from common.validators import validate_minio_config
from config.settings import get_settings
from storage.paths import build_object_key


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


def test_bronze_path_builder() -> None:
    key = build_object_key("bronze", "ccu", filename="event.json")
    assert key.startswith("bronze/ccu/")


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
