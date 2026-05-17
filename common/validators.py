"""Validation helpers for ingestion and configuration."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, Mapping, Optional
from urllib.parse import urlparse

from common.exceptions import ValidationError

SOURCE_STATUS_VALUES = frozenset({"success", "failed", "stale"})
_METADATA_REQUIRED = frozenset({"source", "entity", "ingested_at", "correlation_id"})


def validate_ccu(player_count: Any) -> int:
    """Validate CCU is a non-negative integer."""
    if isinstance(player_count, bool) or not isinstance(player_count, int):
        raise ValidationError("CCU must be an integer")
    if player_count < 0:
        raise ValidationError("CCU must be non-negative")
    return player_count


def validate_metadata(metadata: Mapping[str, Any]) -> None:
    """Ensure ingestion metadata contains required fields."""
    missing = _METADATA_REQUIRED - set(metadata.keys())
    if missing:
        raise ValidationError(f"Metadata missing required fields: {sorted(missing)}")


def validate_source_status(status: str) -> str:
    """Validate source health status value."""
    if status not in SOURCE_STATUS_VALUES:
        raise ValidationError(
            f"Invalid status '{status}'; allowed: {sorted(SOURCE_STATUS_VALUES)}"
        )
    return status


def validate_timestamp(value: str) -> str:
    """Validate ISO-8601-like datetime string."""
    normalized = value.replace("Z", "+00:00")
    try:
        datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValidationError(f"Invalid timestamp format: {value}") from exc
    return value


_ALLOWED_MINIO_PROFILES = frozenset({"internal", "external"})


def validate_minio_profile(profile: str) -> None:
    """Validate MINIO_PROFILE is internal (local) or external (remote host)."""
    normalized = str(profile).strip().lower()
    if normalized not in _ALLOWED_MINIO_PROFILES:
        raise ValidationError(
            f"MINIO_PROFILE must be one of {sorted(_ALLOWED_MINIO_PROFILES)}; got: {profile}"
        )


def validate_minio_config(config: Mapping[str, Any]) -> None:
    """Validate MinIO configuration completeness."""
    required = (
        "minio_profile",
        "minio_endpoint",
        "minio_access_key",
        "minio_secret_key",
        "minio_bucket",
        "minio_secure",
    )
    missing = [key for key in required if not str(config.get(key, "")).strip()]
    if missing:
        raise ValidationError(f"MinIO config incomplete; missing: {missing}")

    endpoint = str(config["minio_endpoint"]).strip()
    parsed = urlparse(endpoint if "://" in endpoint else f"http://{endpoint}")
    if not parsed.netloc:
        raise ValidationError(f"Invalid MINIO_ENDPOINT: {endpoint}")


def validate_url(url: str) -> str:
    """Validate URL has scheme and host."""
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise ValidationError(f"Invalid URL: {url}")
    return url


def parse_bool(value: Optional[str], default: bool = False) -> bool:
    """Parse boolean from environment string."""
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}
