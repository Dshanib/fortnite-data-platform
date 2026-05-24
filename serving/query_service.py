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

    def _connect(self, *, refresh: bool = True) -> duckdb.DuckDBPyConnection:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = duckdb.connect(str(self._db_path))
        if get_gold_read_mode(self._settings) == GOLD_READ_MODE_DIRECT:
            try:
                configure_duckdb_minio(conn, self._settings)
            except DuckDBMinioConfigError as exc:
                logger.warning("MinIO S3 settings not applied on connect: %s", exc)
        if refresh:
            refresh_views(conn, self._settings, allow_fallback=True)
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

    def get_players_online_summary(self) -> QueryResponse:
        """Total active players for today (calendar day if present, else latest day in Gold)."""
        return self._run_query(
            "get_players_online_summary",
            """
            WITH target_day AS (
                SELECT COALESCE(
                    (
                        SELECT MAX(TRY_CAST(metric_hour AS DATE))
                        FROM vw_island_metric_hourly
                        WHERE TRY_CAST(metric_hour AS DATE) = CURRENT_DATE
                    ),
                    (
                        SELECT MAX(TRY_CAST(metric_hour AS DATE))
                        FROM vw_island_metric_hourly
                    )
                ) AS metric_date
            ),
            day_rows AS (
                SELECT h.*
                FROM vw_island_metric_hourly AS h
                CROSS JOIN target_day AS d
                WHERE TRY_CAST(h.metric_hour AS DATE) = d.metric_date
            ),
            uniq_by_island AS (
                SELECT island_code, MAX(max_value) AS island_unique
                FROM day_rows
                WHERE metric_name = 'uniquePlayers'
                GROUP BY island_code
            ),
            plays_by_island AS (
                SELECT island_code, MAX(max_value) AS island_plays
                FROM day_rows
                WHERE metric_name = 'plays'
                GROUP BY island_code
            ),
            peak_by_hour AS (
                SELECT metric_hour, SUM(max_value) AS platform_peak
                FROM day_rows
                WHERE metric_name = 'peakCCU'
                GROUP BY metric_hour
            ),
            day_bounds AS (
                SELECT
                    MIN(metric_hour) AS first_metric_hour,
                    MAX(metric_hour) AS last_metric_hour,
                    COUNT(DISTINCT metric_hour) AS hours_with_data
                FROM day_rows
                WHERE metric_name = 'uniquePlayers'
            )
            SELECT
                CAST((SELECT metric_date FROM target_day) AS VARCHAR) AS metric_date,
                COALESCE((SELECT SUM(island_unique) FROM uniq_by_island), 0)
                    AS active_players_today,
                COALESCE((SELECT SUM(island_unique) FROM uniq_by_island), 0)
                    AS unique_players_today,
                COALESCE((SELECT SUM(island_plays) FROM plays_by_island), 0) AS plays_today,
                (SELECT COUNT(*) FROM uniq_by_island) AS islands_with_data,
                COALESCE((SELECT MAX(platform_peak) FROM peak_by_hour), 0) AS peak_ccu_today,
                (SELECT first_metric_hour FROM day_bounds) AS first_metric_hour,
                (SELECT last_metric_hour FROM day_bounds) AS last_metric_hour,
                (SELECT hours_with_data FROM day_bounds) AS hours_with_data,
                (SELECT metric_date = CURRENT_DATE FROM target_day) AS is_calendar_today,
                (SELECT last_metric_hour FROM day_bounds) AS data_as_of
            """,
            required_view="vw_island_metric_hourly",
        )

    def get_most_active_island(self) -> QueryResponse:
        """Top island by peak_ccu on the latest metric day with full activity details."""
        return self._run_query(
            "get_most_active_island",
            """
            WITH target_day AS (
                SELECT COALESCE(
                    (
                        SELECT MAX(CAST(latest_metric_timestamp AS DATE))
                        FROM vw_current_island_activity
                        WHERE CAST(latest_metric_timestamp AS DATE) = CURRENT_DATE
                    ),
                    (
                        SELECT MAX(CAST(latest_metric_timestamp AS DATE))
                        FROM vw_current_island_activity
                    )
                ) AS metric_date
            ),
            activity AS (
                SELECT
                    a.island_code,
                    a.title,
                    a.creator_code,
                    a.peak_ccu,
                    a.unique_players,
                    a.plays,
                    a.minutes_played,
                    CAST(a.latest_metric_timestamp AS TIMESTAMPTZ) AS latest_metric_timestamp,
                    CAST((SELECT metric_date FROM target_day) AS DATE) AS metric_date,
                    (SELECT metric_date = CURRENT_DATE FROM target_day) AS is_calendar_today
                FROM vw_current_island_activity AS a
                CROSS JOIN target_day AS d
                WHERE a.peak_ccu IS NOT NULL
                  AND CAST(a.latest_metric_timestamp AS DATE) = d.metric_date
            )
            SELECT
                *,
                (SELECT MAX(latest_metric_timestamp) FROM activity) AS data_as_of
            FROM activity
            ORDER BY peak_ccu DESC NULLS LAST
            LIMIT 1
            """,
            required_view="vw_current_island_activity",
        )

    def get_current_ccu(self) -> QueryResponse:
        """Backward-compatible alias for the most active island summary."""
        response = self.get_most_active_island()
        return QueryResponse(
            query_name="get_current_ccu",
            success=response.success,
            status=response.status,
            data=response.data,
            message=response.message,
        )

    def get_top_islands(self, limit: int = 100) -> QueryResponse:
        """All islands with activity on the latest metric day, ranked by peak CCU."""
        safe_limit = max(1, min(int(limit), 500))
        return self._run_query(
            "get_top_islands",
            f"""
            WITH target_day AS (
                SELECT COALESCE(
                    (
                        SELECT MAX(CAST(latest_metric_timestamp AS DATE))
                        FROM vw_current_island_activity
                        WHERE CAST(latest_metric_timestamp AS DATE) = CURRENT_DATE
                    ),
                    (
                        SELECT MAX(CAST(latest_metric_timestamp AS DATE))
                        FROM vw_current_island_activity
                    )
                ) AS metric_date
            ),
            today AS (
                SELECT
                    a.island_code,
                    a.title,
                    a.peak_ccu,
                    a.unique_players,
                    a.plays,
                    a.minutes_played,
                    CAST(a.latest_metric_timestamp AS TIMESTAMPTZ) AS latest_metric_timestamp,
                    CAST((SELECT metric_date FROM target_day) AS DATE) AS metric_date,
                    (SELECT metric_date = CURRENT_DATE FROM target_day) AS is_calendar_today
                FROM vw_current_island_activity AS a
                CROSS JOIN target_day AS d
                WHERE CAST(a.latest_metric_timestamp AS DATE) = d.metric_date
            ),
            ranked AS (
                SELECT
                    *,
                    ROW_NUMBER() OVER (
                        ORDER BY peak_ccu DESC NULLS LAST, unique_players DESC NULLS LAST
                    ) AS rank
                FROM today
            )
            SELECT
                rank,
                island_code,
                title,
                peak_ccu,
                unique_players,
                plays,
                minutes_played,
                latest_metric_timestamp,
                (SELECT MAX(latest_metric_timestamp) FROM today) AS data_as_of,
                (SELECT MAX(metric_date) FROM today) AS metric_date,
                (SELECT BOOL_OR(is_calendar_today) FROM today) AS is_calendar_today,
                (SELECT COUNT(*) FROM today) AS total_islands
            FROM ranked
            ORDER BY rank ASC
            LIMIT {safe_limit}
            """,
            required_view="vw_current_island_activity",
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

    def get_shop_categories(self) -> QueryResponse:
        """Shop sections (layout_id) for the latest snapshot — matches Fortnite shop layout."""
        return self._run_query(
            "get_shop_categories",
            """
            WITH latest AS (
                SELECT MAX(snapshot_date) AS snapshot_date
                FROM vw_shop_items
            )
            SELECT
                COALESCE(NULLIF(TRIM(s.layout_id), ''), 'other') AS category,
                COUNT(*) AS item_count,
                MAX(s.snapshot_date) AS snapshot_date
            FROM vw_shop_items AS s
            CROSS JOIN latest AS l
            WHERE s.snapshot_date = l.snapshot_date
            GROUP BY 1
            HAVING COUNT(*) > 0
            ORDER BY item_count DESC, category ASC
            """,
            required_view="vw_shop_items",
        )

    def get_shop_items_by_category(self, category: str, *, limit: int = 8) -> QueryResponse:
        """Shop items in a layout section for the latest snapshot."""
        safe_limit = max(1, min(int(limit), 12))
        safe_category = (category or "other").strip().replace("'", "''")[:64]
        return self._run_query(
            "get_shop_items_by_category",
            f"""
            WITH latest AS (
                SELECT MAX(snapshot_date) AS snapshot_date
                FROM vw_shop_items
            ),
            filtered AS (
                SELECT
                    s.offer_id,
                    s.dev_name,
                    COALESCE(
                        c.name,
                        CASE
                            WHEN LENGTH(s.dev_name) > 48
                                THEN SUBSTRING(s.dev_name, 1, 45) || '...'
                            ELSE s.dev_name
                        END
                    ) AS item_name,
                    COALESCE(NULLIF(TRIM(s.layout_id), ''), 'other') AS category,
                    COALESCE(NULLIF(TRIM(c.rarity), ''), 'unknown') AS rarity,
                    s.final_price,
                    s.regular_price,
                    s.snapshot_date
                FROM vw_shop_items AS s
                CROSS JOIN latest AS l
                LEFT JOIN vw_cosmetics AS c ON s.dev_name = c.cosmetic_id
                WHERE s.snapshot_date = l.snapshot_date
                  AND LOWER(COALESCE(NULLIF(TRIM(s.layout_id), ''), 'other'))
                      = LOWER('{safe_category}')
            )
            SELECT
                f.*,
                (SELECT COUNT(*) FROM filtered) AS total_in_category
            FROM filtered AS f
            ORDER BY f.final_price DESC NULLS LAST, f.item_name ASC
            LIMIT {safe_limit}
            """,
            required_view="vw_shop_items",
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

    def get_data_freshness(self) -> QueryResponse:
        """Pipeline + Gold timestamps for bot freshness footer."""
        return self._run_query(
            "get_data_freshness",
            """
            WITH latest_metric_day AS (
                SELECT COALESCE(
                    (
                        SELECT MAX(TRY_CAST(metric_hour AS DATE))
                        FROM vw_island_metric_hourly
                        WHERE TRY_CAST(metric_hour AS DATE) = CURRENT_DATE
                    ),
                    (
                        SELECT MAX(TRY_CAST(metric_hour AS DATE))
                        FROM vw_island_metric_hourly
                    )
                ) AS metric_date
            )
            SELECT
                (SELECT MAX(last_success_at)
                 FROM vw_source_health_summary
                 WHERE source_name = 'fortnite_ecosystem_api') AS metrics_pipeline_at,
                (SELECT MAX(last_success_at)
                 FROM vw_source_health_summary
                 WHERE source_name = 'fortnite_api_com') AS shop_pipeline_at,
                (SELECT MAX(TRY_CAST(metric_hour AS TIMESTAMPTZ))
                 FROM vw_island_metric_hourly) AS latest_metric_hour,
                (SELECT MAX(CAST(latest_metric_timestamp AS TIMESTAMPTZ))
                 FROM vw_current_island_activity) AS latest_activity_at,
                (SELECT MAX(snapshot_date)
                 FROM vw_shop_rarity_distribution) AS latest_shop_snapshot,
                CAST((SELECT metric_date FROM latest_metric_day) AS VARCHAR)
                    AS latest_metric_date,
                (SELECT metric_date = CURRENT_DATE FROM latest_metric_day)
                    AS metric_day_is_today,
                (
                    SELECT COUNT(DISTINCT island_code)
                    FROM vw_island_metric_hourly AS h
                    CROSS JOIN latest_metric_day AS d
                    WHERE TRY_CAST(h.metric_hour AS DATE) = d.metric_date
                ) AS islands_on_metric_day
            """,
            required_view="vw_source_health_summary",
        )
