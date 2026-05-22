"""Legacy serving test — see tests/test_query_service.py."""

from __future__ import annotations

from config.settings import get_settings
from serving.query_service import QueryService


def test_query_no_data_on_missing_gold(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("GOLD_DATA_ROOT", str(tmp_path / "no_gold"))
    monkeypatch.setenv("DUCKDB_PATH", str(tmp_path / "legacy.duckdb"))
    get_settings.cache_clear()
    service = QueryService(get_settings(), auto_init=True)
    response = service.get_current_ccu()
    assert response.query_name == "get_current_ccu"
    assert response.status == "no_data"
    assert response.data == []
