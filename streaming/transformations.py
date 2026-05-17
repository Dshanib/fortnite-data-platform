"""Pure-Python Bronze event transforms (testable without Spark)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from common.logging import get_logger

logger = get_logger(__name__)

METRIC_NAMES = ("peakCCU", "uniquePlayers", "plays", "minutesPlayed")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _nested_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("value", "name", "id", "text"):
            if key in value and value[key] is not None:
                return str(value[key])
    return str(value)


def _nested_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _event_meta(event: Dict[str, Any]) -> tuple[str, str]:
    event_id = str(event.get("event_id") or "")
    ingested_at = str(event.get("ingested_at") or event.get("event_time") or "")
    return event_id, ingested_at


def _shop_entries(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    data = payload.get("data")
    if not isinstance(data, dict):
        return []
    for key in ("entries", "featured", "daily"):
        entries = data.get(key)
        if isinstance(entries, list) and entries:
            return [e for e in entries if isinstance(e, dict)]
    for value in data.values():
        if isinstance(value, list) and value and isinstance(value[0], dict):
            return value
    return []


def transform_shop_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Flatten shop bronze envelopes to shop_items rows."""
    rows: List[Dict[str, Any]] = []
    processed_at = _utc_now()

    for event in events:
        payload = event.get("payload")
        if not isinstance(payload, dict):
            logger.warning("Shop event missing payload event_id=%s", event.get("event_id"))
            continue

        source_event_id, ingested_at = _event_meta(event)
        data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        snapshot_date = str(data.get("date") or event.get("event_time", ""))[:10] or None
        entries = _shop_entries(payload)

        if not entries:
            logger.warning("Shop payload has no entries event_id=%s", source_event_id)
            continue

        for entry in entries:
            offer_id = entry.get("offerId") or entry.get("offer_id")
            if not offer_id:
                continue
            layout = entry.get("layout")
            layout_id = None
            if isinstance(layout, dict):
                layout_id = layout.get("id") or layout.get("name")
            elif layout is not None:
                layout_id = str(layout)

            rows.append(
                {
                    "snapshot_date": snapshot_date,
                    "offer_id": str(offer_id),
                    "dev_name": entry.get("devName") or entry.get("dev_name"),
                    "regular_price": _nested_float(
                        entry.get("regularPrice") or entry.get("regular_price")
                    ),
                    "final_price": _nested_float(
                        entry.get("finalPrice") or entry.get("final_price")
                    ),
                    "giftable": entry.get("giftable"),
                    "refundable": entry.get("refundable"),
                    "in_date": entry.get("inDate") or entry.get("in_date"),
                    "out_date": entry.get("outDate") or entry.get("out_date"),
                    "layout_id": layout_id,
                    "source_event_id": source_event_id,
                    "ingested_at": ingested_at,
                    "processed_at": processed_at,
                }
            )

    return rows


def _cosmetics_records(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    data = payload.get("data")
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    if isinstance(data, dict):
        return [r for r in data.values() if isinstance(r, dict)]
    return []


def transform_cosmetics_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Flatten cosmetics bronze envelopes (including chunked batches)."""
    rows: List[Dict[str, Any]] = []
    processed_at = _utc_now()

    for event in events:
        payload = event.get("payload")
        if not isinstance(payload, dict):
            logger.warning(
                "Cosmetics event missing payload event_id=%s", event.get("event_id")
            )
            continue

        source_event_id, ingested_at = _event_meta(event)
        records = _cosmetics_records(payload)
        if not records:
            logger.warning("Cosmetics payload empty event_id=%s", source_event_id)
            continue

        for record in records:
            cosmetic_id = record.get("id") or record.get("cosmeticId")
            if not cosmetic_id:
                continue
            intro = record.get("introduction")
            intro_text = None
            if isinstance(intro, dict):
                intro_text = intro.get("text") or intro.get("backendValue")
            elif isinstance(intro, str):
                intro_text = intro

            set_field = record.get("set")
            set_name = _nested_str(set_field) if set_field else None

            rows.append(
                {
                    "cosmetic_id": str(cosmetic_id),
                    "name": record.get("name"),
                    "description": record.get("description"),
                    "rarity": _nested_str(record.get("rarity")),
                    "type": _nested_str(record.get("type")),
                    "set_name": set_name,
                    "introduction_text": intro_text,
                    "source_event_id": source_event_id,
                    "ingested_at": ingested_at,
                    "processed_at": processed_at,
                }
            )

    return rows


def transform_islands_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Flatten islands bronze envelopes."""
    rows: List[Dict[str, Any]] = []
    processed_at = _utc_now()

    for event in events:
        payload = event.get("payload")
        if not isinstance(payload, dict):
            logger.warning(
                "Islands event missing payload event_id=%s", event.get("event_id")
            )
            continue

        source_event_id, ingested_at = _event_meta(event)
        data = payload.get("data")
        if not isinstance(data, list):
            logger.warning("Islands payload missing data[] event_id=%s", source_event_id)
            continue

        for island in data:
            if not isinstance(island, dict):
                continue
            island_code = island.get("code") or island.get("displayName")
            if not island_code:
                continue
            tags = island.get("tags")
            tags_str = None
            if isinstance(tags, list):
                tags_str = json.dumps(tags)
            elif tags is not None:
                tags_str = str(tags)

            rows.append(
                {
                    "island_code": str(island_code),
                    "title": island.get("title"),
                    "creator_code": island.get("creatorCode") or island.get("creator_code"),
                    "display_name": island.get("displayName") or island.get("display_name"),
                    "category": _nested_str(island.get("category")),
                    "created_in": island.get("createdIn") or island.get("created_in"),
                    "tags": tags_str,
                    "source_event_id": source_event_id,
                    "ingested_at": ingested_at,
                    "processed_at": processed_at,
                }
            )

    return rows


def _island_code_from_event(event: Dict[str, Any], payload: Dict[str, Any]) -> Optional[str]:
    for key in ("islandCode", "island_code", "code"):
        if payload.get(key):
            return str(payload[key])
    event_id = str(event.get("event_id") or "")
    if ":" in event_id:
        return event_id.rsplit(":", 1)[-1]
    return None


def _metric_points(metric_body: Any) -> List[Dict[str, Any]]:
    """Extract timestamp/value points from a metric API fragment."""
    if not isinstance(metric_body, dict):
        return []

    series = metric_body.get("data")
    if isinstance(series, list):
        return [p for p in series if isinstance(p, dict)]

    if isinstance(series, dict):
        points: List[Dict[str, Any]] = []
        for key, value in series.items():
            if isinstance(value, dict):
                points.append(
                    {
                        "timestamp": value.get("timestamp")
                        or value.get("time")
                        or key,
                        "value": value.get("value") if "value" in value else value.get("count"),
                    }
                )
            else:
                points.append({"timestamp": key, "value": value})
        return points

    return []


def _interval_type(payload: Dict[str, Any]) -> str:
    return str(
        payload.get("interval")
        or payload.get("intervalType")
        or payload.get("interval_type")
        or "minute"
    )


def transform_island_metrics_events(
    events: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Normalize island metrics to long format."""
    rows: List[Dict[str, Any]] = []
    processed_at = _utc_now()

    for event in events:
        payload = event.get("payload")
        if not isinstance(payload, dict):
            logger.warning(
                "Island metrics event missing payload event_id=%s",
                event.get("event_id"),
            )
            continue

        source_event_id, ingested_at = _event_meta(event)
        island_code = _island_code_from_event(event, payload)
        if not island_code:
            logger.warning(
                "Island metrics missing island_code event_id=%s", source_event_id
            )
            continue

        interval_type = _interval_type(payload)
        metric_keys = [name for name in METRIC_NAMES if name in payload]
        if not metric_keys and isinstance(payload.get("metrics"), dict):
            metric_keys = list(payload["metrics"].keys())

        if not metric_keys:
            logger.warning(
                "Island metrics payload has no known metrics event_id=%s",
                source_event_id,
            )
            continue

        for metric_name in metric_keys:
            body = payload.get(metric_name)
            if body is None and isinstance(payload.get("metrics"), dict):
                body = payload["metrics"].get(metric_name)
            for point in _metric_points(body):
                ts = point.get("timestamp") or point.get("time")
                if not ts:
                    continue
                metric_timestamp = str(ts)
                metric_date = metric_timestamp[:10]
                rows.append(
                    {
                        "island_code": island_code,
                        "interval_type": interval_type,
                        "metric_name": metric_name,
                        "metric_timestamp": metric_timestamp,
                        "metric_date": metric_date,
                        "metric_value": _nested_float(
                            point.get("value") if "value" in point else point.get("count")
                        ),
                        "source_event_id": source_event_id,
                        "ingested_at": ingested_at,
                        "processed_at": processed_at,
                    }
                )

    return rows
