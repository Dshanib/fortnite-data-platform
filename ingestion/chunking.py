"""Split large API payloads into Kafka-sized chunks."""

from __future__ import annotations

import math
from copy import deepcopy
from typing import Any, Dict, Iterator, List

from common.exceptions import IngestionError


def extract_cosmetics_records(body: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return cosmetics list from a Fortnite-API /v2/cosmetics/br body."""
    data = body.get("data") or []
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        return [item for item in data.values() if isinstance(item, dict)]
    return []


def iter_cosmetics_chunk_payloads(
    full_body: Dict[str, Any],
    *,
    chunk_size: int,
    correlation_id: str,
) -> Iterator[Dict[str, Any]]:
    """Yield API-shaped payloads with a slice of cosmetics per batch."""
    if chunk_size < 1:
        raise IngestionError("Cosmetics chunk size must be at least 1")

    records = extract_cosmetics_records(full_body)
    if not records:
        raise IngestionError("Fortnite-API cosmetics response was empty")

    batch_count = math.ceil(len(records) / chunk_size)
    for batch_index in range(batch_count):
        start = batch_index * chunk_size
        end = start + chunk_size
        chunk_records = records[start:end]
        payload = deepcopy(full_body)
        payload["data"] = chunk_records
        payload["ingestion_batch"] = {
            "correlation_id": correlation_id,
            "batch_index": batch_index,
            "batch_count": batch_count,
            "batch_size": len(chunk_records),
            "total_records": len(records),
        }
        yield payload
