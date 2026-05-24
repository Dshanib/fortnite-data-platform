"""Legacy storage path tests (non-bronze hive layout)."""

from __future__ import annotations

from storage.paths import build_object_key


def test_bronze_path_builder_legacy() -> None:
    key = build_object_key("bronze", "ccu", filename="event.json")
    assert key.startswith("bronze/ccu/")


def test_silver_and_gold_path_builders() -> None:
    silver = build_object_key("silver", "shop", filename="event.json")
    gold = build_object_key("gold", "shop", filename="event.json")
    assert silver.startswith("silver/shop/")
    assert gold.startswith("gold/shop/")
