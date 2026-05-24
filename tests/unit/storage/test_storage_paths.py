"""Bronze storage path unit tests."""

from __future__ import annotations

from datetime import date

import pytest

from common.exceptions import StorageError
from storage.paths import (
    build_bronze_filename,
    build_bronze_object_key,
    build_bronze_prefix,
    parse_event_date,
    resolve_bronze_source,
)


def test_build_bronze_prefix() -> None:
    prefix = build_bronze_prefix("shop", date(2026, 5, 17))
    assert prefix == "bronze/source=shop/event_date=2026-05-17/"


def test_build_bronze_object_key() -> None:
    key = build_bronze_object_key(
        "cosmetics",
        date(2026, 5, 17),
        filename="raw_cosmetics_test.json",
    )
    assert key == (
        "bronze/source=cosmetics/event_date=2026-05-17/raw_cosmetics_test.json"
    )


def test_build_bronze_filename() -> None:
    name = build_bronze_filename(
        "islands",
        event_id="abc-123",
        event_time="2026-05-17T12:00:00+00:00",
    )
    assert name.startswith("raw_islands_")
    assert name.endswith("_abc-123.json")


def test_parse_event_date_from_event_time() -> None:
    event = {"event_time": "2026-05-17T17:00:00+00:00"}
    assert parse_event_date(event) == date(2026, 5, 17)


def test_resolve_bronze_source_from_topic() -> None:
    event = {"event_type": "shop"}
    assert resolve_bronze_source(event, topic="fortnite.raw.shop") == "shop"


def test_resolve_bronze_source_health_event() -> None:
    event = {
        "source": "fortnite_api_com",
        "entity": "shop",
        "status": "success",
        "observed_at": "2026-05-17T12:00:00+00:00",
    }
    assert (
        resolve_bronze_source(event, topic="fortnite.ops.ingestion_status")
        == "ingestion_status"
    )


def test_resolve_bronze_source_unknown() -> None:
    with pytest.raises(StorageError):
        resolve_bronze_source({}, topic=None)
