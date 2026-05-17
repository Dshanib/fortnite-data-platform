"""Cosmetics Kafka chunking tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from config.settings import get_settings
from ingestion.chunking import extract_cosmetics_records, iter_cosmetics_chunk_payloads
from ingestion.clients.api_result import ApiFetchResult
from ingestion.ingest_cosmetics import run_ingestion


def test_extract_cosmetics_records_list() -> None:
    body = {"status": 200, "data": [{"id": "a"}, {"id": "b"}]}
    assert len(extract_cosmetics_records(body)) == 2


def test_iter_cosmetics_chunk_payloads() -> None:
    body = {"status": 200, "data": [{"id": str(i)} for i in range(5)]}
    chunks = list(
        iter_cosmetics_chunk_payloads(
            body, chunk_size=2, correlation_id="corr-1"
        )
    )
    assert len(chunks) == 3
    assert len(chunks[0]["data"]) == 2
    assert len(chunks[2]["data"]) == 1
    assert chunks[0]["ingestion_batch"]["batch_count"] == 3
    assert chunks[0]["ingestion_batch"]["total_records"] == 5


@patch("ingestion.ingest_cosmetics.FortniteApiClient")
def test_ingest_cosmetics_publishes_chunks(mock_client_cls: MagicMock) -> None:
    settings = get_settings()
    records = [{"id": str(i)} for i in range(5)]
    fetch = ApiFetchResult(
        status_code=200,
        latency_ms=10.0,
        body={"status": 200, "data": records},
        fetched_at="2026-05-17T12:00:00+00:00",
    )
    mock_client_cls.return_value.fetch_cosmetics.return_value = fetch

    with patch("ingestion.ingest_cosmetics.IngestionPipeline") as mock_pipeline_cls:
        pipeline = mock_pipeline_cls.return_value
        pipeline.correlation_id = "corr-1"
        code = run_ingestion(settings)

    assert code == 0
    pipeline.run_publish_chunked.assert_called_once()
    kwargs = pipeline.run_publish_chunked.call_args.kwargs
    assert kwargs["total_record_count"] == 5
    published = list(kwargs["chunk_payloads"])
    assert len(published) == 1  # default chunk size 400; five records fit in one message
