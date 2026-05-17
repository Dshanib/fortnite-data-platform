"""Validator unit tests."""

from __future__ import annotations

import pytest

from common.exceptions import ValidationError
from common.validators import (
    validate_ccu,
    validate_metadata,
    validate_minio_config,
    validate_source_status,
    validate_timestamp,
)


def test_validate_ccu_ok() -> None:
    assert validate_ccu(100) == 100


def test_validate_ccu_negative() -> None:
    with pytest.raises(ValidationError):
        validate_ccu(-1)


def test_validate_metadata_missing() -> None:
    with pytest.raises(ValidationError):
        validate_metadata({"source": "x"})


def test_validate_source_status() -> None:
    assert validate_source_status("success") == "success"
    with pytest.raises(ValidationError):
        validate_source_status("broken")


def test_validate_timestamp() -> None:
    validate_timestamp("2026-05-17T12:00:00+00:00")


def test_validate_minio_config() -> None:
    validate_minio_config(
        {
            "minio_profile": "internal",
            "minio_endpoint": "http://localhost:9000",
            "minio_access_key": "key",
            "minio_secret_key": "secret",
            "minio_bucket": "bucket",
            "minio_secure": False,
        }
    )
