"""Query service no-data behavior tests."""

from __future__ import annotations

from config.settings import get_settings
from serving.duckdb_init import init_duckdb
from serving.query_service import QueryService


def test_query_no_data_on_empty_tables(tmp_path) -> None:
    settings = get_settings()
    init_duckdb(settings)
    service = QueryService(settings)
    response = service.get_current_ccu()
    assert response.query_name == "get_current_ccu"
    assert response.success is False
    assert "No data" in response.message
