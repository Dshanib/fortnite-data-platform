"""Island catalog pagination helpers for Kafka-sized ingestion."""

from __future__ import annotations

from typing import Any, Dict, Iterator, List, Optional, Tuple

from ingestion.clients.api_result import ApiFetchResult
from ingestion.clients.ecosystem_api_client import EcosystemApiClient

# Epic catalog can return 250+ pages; cap unless explicitly raised in env.
HARD_MAX_ISLAND_PAGES = 500


def effective_page_cap(requested: int) -> int:
    """0 means use HARD_MAX_ISLAND_PAGES as safety ceiling."""
    if requested <= 0:
        return HARD_MAX_ISLAND_PAGES
    return min(requested, HARD_MAX_ISLAND_PAGES)


def iter_island_catalog_pages(
    client: EcosystemApiClient,
    *,
    page_size: int,
    max_pages: int,
) -> Iterator[Tuple[int, ApiFetchResult, List[Dict[str, Any]]]]:
    """
    Yield one API page at a time (island list + fetch metadata).

    Stops on empty batch, missing cursor, short page, or duplicate cursor.
    """
    page_cap = effective_page_cap(max_pages)
    after: Optional[str] = None
    seen_cursors: set[str] = set()

    for page_index in range(page_cap):
        fetch = client.fetch_islands(size=page_size, after=after)
        body = fetch.body if isinstance(fetch.body, dict) else {}
        batch = body.get("data") or []
        if not isinstance(batch, list):
            batch = []

        islands = [item for item in batch if isinstance(item, dict)]
        yield page_index, fetch, islands

        if not islands:
            break

        cursor = client._next_page_cursor(body)
        if not cursor:
            break
        if len(islands) < page_size:
            break
        if cursor in seen_cursors:
            break
        seen_cursors.add(cursor)
        after = cursor


def build_island_page_payload(
    *,
    page_index: int,
    islands: List[Dict[str, Any]],
    correlation_id: str,
) -> Dict[str, Any]:
    """Build a Kafka payload for one catalog page."""
    return {
        "data": islands,
        "ingestion_batch": {
            "correlation_id": correlation_id,
            "batch_index": page_index,
            "batch_size": len(islands),
        },
        "meta": {
            "page_index": page_index,
            "page_size": len(islands),
        },
    }
