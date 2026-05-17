"""Object storage path helpers for medallion layers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

LAYER_BRONZE = "bronze"
LAYER_SILVER = "silver"
LAYER_GOLD = "gold"


def _date_partition(ts: Optional[datetime] = None) -> str:
    moment = ts or datetime.now(timezone.utc)
    return moment.strftime("%Y/%m/%d")


def build_object_key(
    layer: str,
    entity: str,
    *,
    filename: str,
    ts: Optional[datetime] = None,
) -> str:
    """Build entity-specific object key under a medallion layer."""
    if layer not in {LAYER_BRONZE, LAYER_SILVER, LAYER_GOLD}:
        raise ValueError(f"Unknown layer: {layer}")
    partition = _date_partition(ts)
    return f"{layer}/{entity}/{partition}/{filename}"
