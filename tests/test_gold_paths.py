"""Gold path resolution tests."""

from __future__ import annotations

from config.settings import get_settings
from serving.gold_paths import resolve_gold_paths
from serving.minio_duckdb import GOLD_READ_MODE_DIRECT, GOLD_READ_MODE_LOCAL


def test_direct_minio_path_generation(monkeypatch) -> None:
    monkeypatch.setenv("DUCKDB_GOLD_READ_MODE", GOLD_READ_MODE_DIRECT)
    get_settings.cache_clear()
    settings = get_settings()
    paths = resolve_gold_paths(settings, mode=GOLD_READ_MODE_DIRECT)

    assert paths.read_mode == GOLD_READ_MODE_DIRECT
    assert paths.current_island_activity == (
        f"s3://{settings.minio_bucket}/gold/current_island_activity/**/*.parquet"
    )
    assert paths.top_islands_by_peak_ccu.startswith("s3://")
    assert "secret" not in (paths.current_island_activity or "").lower()


def test_local_cache_path_generation(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DUCKDB_GOLD_READ_MODE", GOLD_READ_MODE_LOCAL)
    monkeypatch.setenv("GOLD_DATA_ROOT", str(tmp_path / "gold"))
    get_settings.cache_clear()
    settings = get_settings()
    paths = resolve_gold_paths(settings, mode=GOLD_READ_MODE_LOCAL)

    assert paths.read_mode == GOLD_READ_MODE_LOCAL
    assert paths.shop_rarity_distribution is None or "s3://" not in (
        paths.shop_rarity_distribution or ""
    )
