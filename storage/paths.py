"""Object storage path helpers for medallion layers."""

from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import Any, Dict, Optional

from common.exceptions import StorageError

LAYER_BRONZE = "bronze"
LAYER_SILVER = "silver"
LAYER_GOLD = "gold"

BRONZE_SOURCE_SHOP = "shop"
BRONZE_SOURCE_COSMETICS = "cosmetics"
BRONZE_SOURCE_ISLANDS = "islands"
BRONZE_SOURCE_ISLAND_METRICS = "island_metrics"
BRONZE_SOURCE_INGESTION_STATUS = "ingestion_status"

BRONZE_SOURCES = frozenset(
    {
        BRONZE_SOURCE_SHOP,
        BRONZE_SOURCE_COSMETICS,
        BRONZE_SOURCE_ISLANDS,
        BRONZE_SOURCE_ISLAND_METRICS,
        BRONZE_SOURCE_INGESTION_STATUS,
    }
)

TOPIC_TO_BRONZE_SOURCE: Dict[str, str] = {
    "fortnite.raw.shop": BRONZE_SOURCE_SHOP,
    "fortnite.raw.cosmetics": BRONZE_SOURCE_COSMETICS,
    "fortnite.raw.islands": BRONZE_SOURCE_ISLANDS,
    "fortnite.raw.island_metrics": BRONZE_SOURCE_ISLAND_METRICS,
    "fortnite.ops.ingestion_status": BRONZE_SOURCE_INGESTION_STATUS,
}

_ISO_DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})")


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
    """Build legacy entity/date path (used by sample upload scripts)."""
    if layer not in {LAYER_BRONZE, LAYER_SILVER, LAYER_GOLD}:
        raise ValueError(f"Unknown layer: {layer}")
    partition = _date_partition(ts)
    return f"{layer}/{entity}/{partition}/{filename}"


def parse_event_date(event: Dict[str, Any]) -> date:
    """Derive partition date from event_time, ingested_at, or observed_at."""
    for field in ("event_time", "ingested_at", "observed_at"):
        raw = event.get(field)
        if not raw:
            continue
        text = str(raw).strip()
        match = _ISO_DATE_RE.match(text)
        if match:
            return date.fromisoformat(match.group(1))
        try:
            normalized = text.replace("Z", "+00:00")
            return datetime.fromisoformat(normalized).date()
        except ValueError:
            continue
    return datetime.now(timezone.utc).date()


def resolve_bronze_source(event: Dict[str, Any], topic: Optional[str] = None) -> str:
    """Map a Kafka message to a bronze source partition name."""
    if topic:
        mapped = TOPIC_TO_BRONZE_SOURCE.get(topic)
        if mapped:
            return mapped

    event_type = str(event.get("event_type") or "").strip()
    if event_type in BRONZE_SOURCES:
        return event_type

    entity = str(event.get("entity") or "").strip()
    if entity == "island_metrics":
        return BRONZE_SOURCE_ISLAND_METRICS
    if entity in BRONZE_SOURCES:
        return entity

    if event.get("source") and event.get("status") and not event.get("event_id"):
        return BRONZE_SOURCE_INGESTION_STATUS

    raise StorageError(
        "Cannot infer bronze source from event; provide topic or event_type/entity"
    )


def build_bronze_prefix(source: str, event_date: date) -> str:
    """Hive-style bronze prefix: bronze/source=shop/event_date=YYYY-MM-DD/"""
    if source not in BRONZE_SOURCES:
        raise StorageError(f"Unknown bronze source: {source}")
    return f"{LAYER_BRONZE}/source={source}/event_date={event_date.isoformat()}/"


def build_bronze_filename(source: str, *, event_id: str, event_time: str) -> str:
    """Filename: raw_<source>_<timestamp>_<uuid>.json"""
    compact_time = (
        str(event_time)
        .replace(":", "")
        .replace("-", "")
        .replace("+00:00", "Z")
        .replace(".", "")
    )[:15]
    safe_id = event_id.replace(":", "-")
    return f"raw_{source}_{compact_time}_{safe_id}.json"


def build_bronze_object_key(
    source: str,
    event_date: date,
    *,
    filename: str,
) -> str:
    """Full object key under the bronze bucket."""
    return f"{build_bronze_prefix(source, event_date)}{filename}"


def bronze_topics() -> tuple[str, ...]:
    """Kafka topics persisted to bronze by default."""
    return tuple(TOPIC_TO_BRONZE_SOURCE.keys())
