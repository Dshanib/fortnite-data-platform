"""Predefined DuckDB query interface over Gold Parquet views."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import duckdb

from common.logging import get_logger
from common.models import QueryResponse
from config.settings import Settings, get_settings
from serving.duckdb_init import init_duckdb, refresh_views, view_exists
from serving.minio_duckdb import (
    GOLD_READ_MODE_DIRECT,
    DuckDBMinioConfigError,
    configure_duckdb_minio,
    get_gold_read_mode,
)

logger = get_logger(__name__)


class QueryService:
    """Safe, predefined queries for bot and API consumers."""

    def __init__(self, settings: Optional[Settings] = None, *, auto_init: bool = True) -> None:
        self._settings = settings or get_settings()
        self._db_path = Path(self._settings.duckdb_path)
        if auto_init:
            self._ensure_initialized()

    def _ensure_initialized(self) -> None:
        conn = duckdb.connect(str(self._db_path))
        try:
            refresh_views(conn, self._settings, allow_fallback=True)
        finally:
            conn.close()

    def _connect(self) -> duckdb.DuckDBPyConnection:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = duckdb.connect(str(self._db_path))
        if get_gold_read_mode(self._settings) == GOLD_READ_MODE_DIRECT:
            try:
                configure_duckdb_minio(conn, self._settings)
            except DuckDBMinioConfigError as exc:
                logger.warning("MinIO S3 settings not applied on connect: %s", exc)
        return conn

    @staticmethod
    def _no_data(query_name: str, message: str) -> QueryResponse:
        return QueryResponse(
            query_name=query_name,
            success=False,
            status="no_data",
            data=[],
            message=message,
        )

    @staticmethod
    def _ok(query_name: str, data: List[Dict[str, Any]], message: str = "OK") -> QueryResponse:
        return QueryResponse(
            query_name=query_name,
            success=True,
            status="ok",
            data=data,
            message=message,
        )

    @staticmethod
    def _error(query_name: str, message: str) -> QueryResponse:
        return QueryResponse(
            query_name=query_name,
            success=False,
            status="error",
            data=[],
            message=message,
        )

    def _run_query(
        self,
        query_name: str,
        sql: str,
        *,
        required_view: str,
    ) -> QueryResponse:
        if not self._db_path.is_file():
            return self._no_data(
                query_name,
                f"DuckDB file missing at {self._db_path}. Run scripts/check_duckdb_serving.py",
            )

        try:
            conn = self._connect()
            if not view_exists(conn, required_view):
                conn.close()
                return self._no_data(
                    query_name,
                    f"View '{required_view}' not available. Sync Gold Parquet and refresh views.",
                )

            cursor = conn.execute(sql)
            columns = [col[0] for col in cursor.description] if cursor.description else []
            raw_rows = cursor.fetchall()
            conn.close()

            if not raw_rows:
                return self._no_data(query_name, "No rows returned from Gold dataset")

            data = [dict(zip(columns, row)) for row in raw_rows]
            return self._ok(query_name, data)
        except duckdb.Error as exc:
            logger.error("Query %s failed: %s", query_name, exc)
            return self._error(query_name, f"Query error: {exc}")

    def get_current_ccu(self) -> QueryResponse:
        """Top island by peak_ccu and sum of visible peak_ccu across islands."""
        return self._run_query(
            "get_current_ccu",
            """
            WITH activity AS (
                SELECT island_code, title, peak_ccu, latest_metric_timestamp
                FROM vw_current_island_activity
                WHERE peak_ccu IS NOT NULL
            )
            SELECT
                island_code,
                title,
                peak_ccu,
                (SELECT COALESCE(SUM(peak_ccu), 0) FROM activity) AS total_peak_ccu,
                latest_metric_timestamp
            FROM activity
            ORDER BY peak_ccu DESC
            LIMIT 1
            """,
            required_view="vw_current_island_activity",
        )

    def get_top_islands(self, limit: int = 10) -> QueryResponse:
        """Ranked islands from gold top_islands_by_peak_ccu."""
        safe_limit = max(1, min(int(limit), 100))
        return self._run_query(
            "get_top_islands",
            f"""
            SELECT rank, island_code, title, peak_ccu, unique_players, plays,
                   latest_metric_timestamp
            FROM vw_top_islands_by_peak_ccu
            ORDER BY rank ASC
            LIMIT {safe_limit}
            """,
            required_view="vw_top_islands_by_peak_ccu",
        )

    def get_avg_today(self) -> QueryResponse:
        """Average peak CCU for UTC today, or latest available date if today is empty."""
        return self._run_query(
            "get_avg_today",
            """
            WITH peak AS (
                SELECT metric_hour, avg_value
                FROM vw_island_metric_hourly
                WHERE metric_name = 'peakCCU'
            ),
            today AS (
                SELECT
                    AVG(avg_value) AS avg_peak_ccu,
                    COUNT(*) AS hourly_buckets,
                    CAST(MAX(metric_hour) AS VARCHAR) AS latest_hour,
                    'today' AS period_label
                FROM peak
                WHERE TRY_CAST(metric_hour AS DATE) = CURRENT_DATE
                HAVING COUNT(*) > 0
            ),
            latest_day AS (
                SELECT MAX(TRY_CAST(metric_hour AS DATE)) AS metric_date
                FROM peak
            ),
            fallback AS (
                SELECT
                    AVG(p.avg_value) AS avg_peak_ccu,
                    COUNT(*) AS hourly_buckets,
                    CAST(MAX(p.metric_hour) AS VARCHAR) AS latest_hour,
                    'latest_available' AS period_label
                FROM peak AS p
                CROSS JOIN latest_day AS ld
                WHERE TRY_CAST(p.metric_hour AS DATE) = ld.metric_date
                HAVING COUNT(*) > 0
            )
            SELECT avg_peak_ccu, hourly_buckets, latest_hour, period_label
            FROM today
            UNION ALL
            SELECT avg_peak_ccu, hourly_buckets, latest_hour, period_label
            FROM fallback
            WHERE NOT EXISTS (SELECT 1 FROM today)
            LIMIT 1
            """,
            required_view="vw_island_metric_hourly",
        )

    def get_recent_anomalies(self, limit: int = 10) -> QueryResponse:
        """Recent peakCCU anomalies from gold/island_activity_anomalies."""
        safe_limit = max(1, min(int(limit), 100))
        return self._run_query(
            "get_recent_anomalies",
            f"""
            SELECT
                island_code,
                title,
                metric_timestamp,
                peak_ccu,
                previous_peak_ccu,
                rolling_avg_peak_ccu,
                pct_change_from_previous,
                deviation_from_rolling_avg,
                anomaly_type,
                severity,
                detected_at
            FROM vw_island_activity_anomalies
            ORDER BY metric_timestamp DESC
            LIMIT {safe_limit}
            """,
            required_view="vw_island_activity_anomalies",
        )

    def get_shop_rarity_distribution(self) -> QueryResponse:
        """Shop item counts and share by rarity."""
        return self._run_query(
            "get_shop_rarity_distribution",
            """
            SELECT snapshot_date, rarity, item_count, share_pct, updated_at
            FROM vw_shop_rarity_distribution
            ORDER BY item_count DESC
            """,
            required_view="vw_shop_rarity_distribution",
        )

    def get_source_health(self) -> QueryResponse:
        """Ingestion health summary by source."""
        return self._run_query(
            "get_source_health",
            """
            SELECT source_name, last_success_at, last_failure_at,
                   success_count, failure_count, latest_status
            FROM vw_source_health_summary
            ORDER BY source_name
            """,
            required_view="vw_source_health_summary",
        )
