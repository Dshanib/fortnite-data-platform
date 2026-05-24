"""Initialize DuckDB and refresh Gold Parquet views (MinIO or local cache)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import duckdb

from common.logging import get_logger
from config.settings import Settings, get_settings
from serving.gold_paths import GoldDatasetPaths, resolve_gold_paths
from serving.silver_paths import SilverDatasetPaths, resolve_silver_paths
from serving.minio_duckdb import (
    GOLD_READ_MODE_DIRECT,
    GOLD_READ_MODE_LOCAL,
    DuckDBMinioConfigError,
    configure_duckdb_minio,
    get_gold_read_mode,
)

logger = get_logger(__name__)

_VIEW_NAMES = (
    "vw_current_island_activity",
    "vw_top_islands_by_peak_ccu",
    "vw_island_metric_hourly",
    "vw_island_activity_anomalies",
    "vw_shop_rarity_distribution",
    "vw_source_health_summary",
    "vw_shop_items",
    "vw_cosmetics",
)


def _sql_string(value: str) -> str:
    return value.replace("'", "''")


def _drop_gold_views(conn: duckdb.DuckDBPyConnection) -> None:
    for name in _VIEW_NAMES:
        conn.execute(f"DROP VIEW IF EXISTS {name}")


def _create_views(conn: duckdb.DuckDBPyConnection, paths: GoldDatasetPaths) -> None:
    for dataset, glob_path in paths.as_dict().items():
        view_name = f"vw_{dataset}"
        if not glob_path:
            logger.warning("Skipping view %s: no parquet path for gold/%s", view_name, dataset)
            continue
        sql = (
            f"CREATE OR REPLACE VIEW {view_name} AS "
            f"SELECT * FROM read_parquet('{_sql_string(glob_path)}')"
        )
        conn.execute(sql)
        logger.info("Created view %s [%s] from %s", view_name, paths.read_mode, glob_path)


def _create_silver_views(conn: duckdb.DuckDBPyConnection, paths: SilverDatasetPaths) -> None:
    mapping = {"shop_items": "vw_shop_items", "cosmetics": "vw_cosmetics"}
    for dataset, view_name in mapping.items():
        glob_path = paths.as_dict().get(dataset)
        if not glob_path:
            logger.warning("Skipping view %s: no parquet path for silver/%s", view_name, dataset)
            continue
        sql = (
            f"CREATE OR REPLACE VIEW {view_name} AS "
            f"SELECT * FROM read_parquet('{_sql_string(glob_path)}')"
        )
        conn.execute(sql)
        logger.info("Created view %s [%s] from %s", view_name, paths.read_mode, glob_path)


def _probe_direct_minio(conn: duckdb.DuckDBPyConnection, paths: GoldDatasetPaths) -> bool:
    """Run a lightweight read against one Gold path to validate MinIO access."""
    for glob_path in paths.as_dict().values():
        if not glob_path:
            continue
        conn.execute(
            f"SELECT 1 FROM read_parquet('{_sql_string(glob_path)}') LIMIT 1"
        ).fetchone()
        return True
    return False


def refresh_views(
    conn: duckdb.DuckDBPyConnection,
    settings: Optional[Settings] = None,
    *,
    mode: Optional[str] = None,
    allow_fallback: bool = True,
) -> GoldDatasetPaths:
    """Create or replace Gold views; fall back to local_cache if direct MinIO fails."""
    settings = settings or get_settings()
    active_mode = get_gold_read_mode(settings, mode)
    _drop_gold_views(conn)

    if active_mode == GOLD_READ_MODE_DIRECT:
        try:
            configure_duckdb_minio(conn, settings)
            paths = resolve_gold_paths(settings, mode=GOLD_READ_MODE_DIRECT)
            silver_paths = resolve_silver_paths(settings, mode=GOLD_READ_MODE_DIRECT)
            _create_views(conn, paths)
            _create_silver_views(conn, silver_paths)
            _probe_direct_minio(conn, paths)
            return paths
        except (DuckDBMinioConfigError, duckdb.Error, OSError, ValueError) as exc:
            if not allow_fallback:
                raise
            logger.warning(
                "direct_minio Gold views failed (%s); falling back to local_cache",
                exc,
            )

    paths = resolve_gold_paths(settings, mode=GOLD_READ_MODE_LOCAL)
    silver_paths = resolve_silver_paths(settings, mode=GOLD_READ_MODE_LOCAL)
    _create_views(conn, paths)
    _create_silver_views(conn, silver_paths)
    return paths


def init_duckdb(
    settings: Optional[Settings] = None,
    *,
    mode: Optional[str] = None,
) -> duckdb.DuckDBPyConnection:
    """Create DuckDB file (if missing) and refresh Gold views."""
    settings = settings or get_settings()
    db_path = Path(settings.duckdb_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = duckdb.connect(str(db_path))
    refresh_views(conn, settings, mode=mode)
    logger.info(
        "DuckDB initialized at %s (requested_mode=%s)",
        db_path,
        get_gold_read_mode(settings, mode),
    )
    return conn


def view_exists(conn: duckdb.DuckDBPyConnection, view_name: str) -> bool:
    row = conn.execute(
        """
        SELECT COUNT(*) FROM information_schema.tables
        WHERE table_name = ? AND table_type = 'VIEW'
        """,
        [view_name],
    ).fetchone()
    return bool(row and row[0] > 0)
