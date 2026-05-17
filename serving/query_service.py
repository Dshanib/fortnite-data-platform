"""Predefined DuckDB query interface (no ad-hoc SQL from callers)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, List, Optional

import duckdb

from common.logging import get_logger
from common.models import QueryResponse
from config.settings import Settings, get_settings

logger = get_logger(__name__)


class QueryService:
    """Safe, predefined queries for bot and API consumers."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or get_settings()
        self._db_path = Path(self._settings.duckdb_path)

    def _connect(self) -> duckdb.DuckDBPyConnection:
        if not self._db_path.is_file():
            logger.warning("DuckDB file missing at %s", self._db_path)
        return duckdb.connect(str(self._db_path))

    def _table_exists(self, conn: duckdb.DuckDBPyConnection, table: str) -> bool:
        row = conn.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
            [table],
        ).fetchone()
        return bool(row and row[0] > 0)

    def _safe_query(
        self,
        query_name: str,
        sql: str,
        *,
        required_table: Optional[str] = None,
    ) -> QueryResponse:
        try:
            conn = self._connect()
            if required_table and not self._table_exists(conn, required_table):
                return QueryResponse(
                    query_name=query_name,
                    success=False,
                    data=None,
                    message=f"No data: table '{required_table}' not available",
                )
            cursor = conn.execute(sql)
            columns = [col[0] for col in cursor.description]
            raw_rows = cursor.fetchall()
            conn.close()
            if not raw_rows:
                return QueryResponse(
                    query_name=query_name,
                    success=False,
                    data=None,
                    message="No data available",
                )
            data = [dict(zip(columns, row)) for row in raw_rows]
            return QueryResponse(
                query_name=query_name,
                success=True,
                data=data,
                message="OK",
            )
        except duckdb.Error as exc:
            logger.error("Query %s failed: %s", query_name, exc)
            return QueryResponse(
                query_name=query_name,
                success=False,
                data=None,
                message=f"Query error: {exc}",
            )

    def get_current_ccu(self) -> QueryResponse:
        """Return latest CCU snapshot."""
        return self._safe_query(
            "get_current_ccu",
            """
            SELECT player_count, captured_at
            FROM ccu_snapshots
            ORDER BY captured_at DESC
            LIMIT 1
            """,
            required_table="ccu_snapshots",
        )

    def get_avg_today(self) -> QueryResponse:
        """Return average CCU for today."""
        return self._safe_query(
            "get_avg_today",
            """
            SELECT AVG(player_count) AS avg_ccu
            FROM ccu_snapshots
            WHERE CAST(captured_at AS DATE) = CURRENT_DATE
            """,
            required_table="ccu_snapshots",
        )

    def get_recent_anomalies(self) -> QueryResponse:
        """Return recent CCU anomalies."""
        return self._safe_query(
            "get_recent_anomalies",
            """
            SELECT player_count, captured_at, z_score
            FROM ccu_anomalies
            ORDER BY captured_at DESC
            LIMIT 10
            """,
            required_table="ccu_anomalies",
        )

    def get_shop_rarity_distribution(self) -> QueryResponse:
        """Return shop item counts by rarity."""
        return self._safe_query(
            "get_shop_rarity_distribution",
            """
            SELECT rarity, COUNT(*) AS item_count
            FROM shop_items
            GROUP BY rarity
            ORDER BY item_count DESC
            """,
            required_table="shop_items",
        )

    def get_source_health(self) -> QueryResponse:
        """Return recent source health events."""
        return self._safe_query(
            "get_source_health",
            """
            SELECT source, entity, status, message, observed_at
            FROM source_health_events
            ORDER BY observed_at DESC
            LIMIT 20
            """,
            required_table="source_health_events",
        )
