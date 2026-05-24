"""Ingestion envelope and pipeline unit tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from common.models import IngestionEventEnvelope
from config.settings import get_settings
from ingestion.clients.api_result import ApiFetchResult
from ingestion.ingest_shop import run_ingestion
from ingestion.pipeline import build_envelope, record_count


def test_build_envelope_fields() -> None:
    fetch = ApiFetchResult(
        status_code=200,
        latency_ms=42.5,
        body={"status": 200, "data": {"entries": [{"id": "a"}]}},
        fetched_at="2026-05-17T12:00:00+00:00",
    )
    envelope = build_envelope(
        event_id="evt-1",
        source_name="fortnite_api_com",
        event_type="shop",
        fetch=fetch,
        ingested_at="2026-05-17T12:00:01+00:00",
    )
    assert envelope.event_id == "evt-1"
    assert envelope.source_name == "fortnite_api_com"
    assert envelope.event_type == "shop"
    assert envelope.event_time == fetch.fetched_at
    assert envelope.ingested_at == "2026-05-17T12:00:01+00:00"
    assert envelope.request_status == "success"
    assert envelope.latency_ms == 42.5
    assert envelope.payload == fetch.body


def test_record_count_shop() -> None:
    payload = {"data": {"entries": [{"id": 1}, {"id": 2}]}}
    assert record_count("shop", payload) == 2


@patch("ingestion.ingest_shop.FortniteApiClient")
def test_ingest_shop_publishes_envelope(mock_client_cls: MagicMock) -> None:
    settings = get_settings()
    fetch = ApiFetchResult(
        status_code=200,
        latency_ms=10.0,
        body={"status": 200, "data": {"entries": [{"id": "x"}]}},
        fetched_at="2026-05-17T12:00:00+00:00",
    )
    mock_client_cls.return_value.fetch_shop.return_value = fetch

    with patch("ingestion.ingest_shop.IngestionPipeline") as mock_pipeline_cls:
        pipeline = mock_pipeline_cls.return_value
        code = run_ingestion(settings)

    assert code == 0
    pipeline.run_publish.assert_called_once()
    kwargs = pipeline.run_publish.call_args.kwargs
    assert kwargs["topic"] == settings.kafka_topic_shop
    assert kwargs["fetch"] is fetch


def test_ingestion_event_envelope_to_dict() -> None:
    envelope = IngestionEventEnvelope(
        event_id="1",
        source_name="src",
        event_type="shop",
        event_time="t1",
        ingested_at="t2",
        request_status="success",
        latency_ms=1.0,
        payload={"ok": True},
    )
    data = envelope.to_dict()
    assert set(data) == {
        "event_id",
        "source_name",
        "event_type",
        "event_time",
        "ingested_at",
        "request_status",
        "latency_ms",
        "payload",
    }
