"""Silver transformation unit tests (no Spark required)."""

from __future__ import annotations

from streaming.transformations import (
    transform_cosmetics_events,
    transform_island_metrics_events,
    transform_islands_events,
    transform_shop_events,
)


def test_transform_shop_events() -> None:
    event = {
        "event_id": "evt-shop",
        "ingested_at": "2026-05-17T12:00:00+00:00",
        "payload": {
            "data": {
                "date": "2026-05-17",
                "entries": [
                    {
                        "offerId": "offer-1",
                        "devName": "TestItem",
                        "finalPrice": 500,
                        "regularPrice": 1000,
                        "giftable": True,
                        "refundable": False,
                        "inDate": "2026-05-01",
                        "outDate": "2026-05-20",
                        "layout": {"id": "layout-1"},
                    }
                ],
            }
        },
    }
    rows = transform_shop_events([event])
    assert len(rows) == 1
    assert rows[0]["offer_id"] == "offer-1"
    assert rows[0]["snapshot_date"] == "2026-05-17"
    assert rows[0]["source_event_id"] == "evt-shop"


def test_transform_shop_drops_missing_offer_id() -> None:
    event = {
        "event_id": "evt-shop",
        "ingested_at": "2026-05-17T12:00:00+00:00",
        "payload": {"data": {"entries": [{"devName": "no-id"}]}},
    }
    assert transform_shop_events([event]) == []


def test_transform_cosmetics_events() -> None:
    event = {
        "event_id": "evt-cos",
        "ingested_at": "2026-05-17T12:00:00+00:00",
        "payload": {
            "data": [
                {
                    "id": "cos-1",
                    "name": "Skin",
                    "description": "Desc",
                    "rarity": {"value": "epic"},
                    "type": {"value": "outfit"},
                    "set": {"value": "Set A"},
                    "introduction": {"text": "Intro"},
                }
            ]
        },
    }
    rows = transform_cosmetics_events([event])
    assert len(rows) == 1
    assert rows[0]["cosmetic_id"] == "cos-1"
    assert rows[0]["rarity"] == "epic"


def test_transform_islands_events() -> None:
    event = {
        "event_id": "evt-islands",
        "ingested_at": "2026-05-17T12:00:00+00:00",
        "payload": {
            "data": [
                {
                    "code": "1234-5678-9012",
                    "title": "Island",
                    "creatorCode": "creator",
                    "displayName": "Island DN",
                    "category": "adventure",
                    "createdIn": "UE5",
                    "tags": ["pvp", "fun"],
                }
            ]
        },
    }
    rows = transform_islands_events([event])
    assert len(rows) == 1
    assert rows[0]["island_code"] == "1234-5678-9012"
    assert "pvp" in (rows[0]["tags"] or "")


def test_transform_island_metrics_long_format() -> None:
    event = {
        "event_id": "corr:ISLAND-ABC",
        "ingested_at": "2026-05-17T12:00:00+00:00",
        "payload": {
            "interval": "minute",
            "peakCCU": {
                "data": [
                    {"timestamp": "2026-05-17T12:00:00Z", "value": 42},
                    {"timestamp": "2026-05-17T12:01:00Z", "value": None},
                ]
            },
            "plays": {
                "data": [{"timestamp": "2026-05-17T12:00:00Z", "value": 10}]
            },
        },
    }
    rows = transform_island_metrics_events([event])
    assert len(rows) == 3
    assert {r["metric_name"] for r in rows} == {"peakCCU", "plays"}
    assert all(r["island_code"] == "ISLAND-ABC" for r in rows)
    assert rows[0]["interval_type"] == "minute"
    null_row = [r for r in rows if r["metric_timestamp"].endswith("12:01:00Z")][0]
    assert null_row["metric_value"] is None
