"""Ecosystem API island pagination helpers."""

from __future__ import annotations

from ingestion.clients.ecosystem_api_client import EcosystemApiClient


def test_next_page_cursor_from_meta() -> None:
    body = {
        "data": [{"code": "A"}],
        "meta": {"page": {"nextCursor": "abc123", "prevCursor": None}},
    }
    assert EcosystemApiClient._next_page_cursor(body) == "abc123"


def test_next_page_cursor_from_links() -> None:
    body = {
        "data": [{"code": "A"}],
        "links": {"next": "/ecosystem/v1/islands?after=xyz%3D&size=100"},
    }
    assert EcosystemApiClient._next_page_cursor(body) == "xyz="


def test_next_page_cursor_none_when_done() -> None:
    body = {"data": [{"code": "A"}], "meta": {"page": {"nextCursor": None}}}
    assert EcosystemApiClient._next_page_cursor(body) is None
