"""Shared utility helpers."""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict

from common.exceptions import ValidationError


def new_correlation_id() -> str:
    """Generate a unique correlation id for tracing ingestion."""
    return str(uuid.uuid4())


def to_json_bytes(payload: Dict[str, Any]) -> bytes:
    """Serialize dict to UTF-8 JSON bytes."""
    return json.dumps(payload, default=str).encode("utf-8")


def safe_int(value: Any, field_name: str) -> int:
    """Parse integer with validation error on failure."""
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{field_name} must be an integer") from exc
