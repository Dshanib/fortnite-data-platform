"""Initialize DuckDB database and apply predefined views."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import duckdb

from common.logging import get_logger
from config.settings import Settings, get_settings

logger = get_logger(__name__)
_VIEWS_SQL = Path(__file__).resolve().parent / "views.sql"


def init_duckdb(settings: Optional[Settings] = None) -> duckdb.DuckDBPyConnection:
    """Create DuckDB file, schema placeholders, and views."""
    settings = settings or get_settings()
    db_path = Path(settings.duckdb_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = duckdb.connect(str(db_path))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ccu_snapshots (
            player_count INTEGER,
            captured_at TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS ccu_anomalies (
            player_count INTEGER,
            captured_at TIMESTAMP,
            z_score DOUBLE
        );
        CREATE TABLE IF NOT EXISTS shop_items (
            item_id VARCHAR,
            name VARCHAR,
            rarity VARCHAR,
            captured_at TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS source_health_events (
            source VARCHAR,
            entity VARCHAR,
            status VARCHAR,
            message VARCHAR,
            observed_at TIMESTAMP
        );
        """
    )

    if _VIEWS_SQL.is_file():
        conn.execute(_VIEWS_SQL.read_text(encoding="utf-8"))
        logger.info("Applied DuckDB views from %s", _VIEWS_SQL)

    logger.info("DuckDB initialized at %s", db_path)
    return conn


if __name__ == "__main__":
    from common.logging import configure_logging

    settings = get_settings()
    configure_logging(settings.log_level)
    init_duckdb(settings)
