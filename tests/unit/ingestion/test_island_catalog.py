"""Island catalog pagination helpers."""

from __future__ import annotations

from ingestion.island_catalog import effective_page_cap


def test_effective_page_cap_zero_uses_hard_limit() -> None:
    assert effective_page_cap(0) == 500


def test_effective_page_cap_clamps_high_values() -> None:
    assert effective_page_cap(9999) == 500
    assert effective_page_cap(30) == 30
