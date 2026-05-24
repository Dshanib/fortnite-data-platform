"""Centralized application settings loaded from environment."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

from common.exceptions import ConfigError
from common.validators import parse_bool, validate_minio_config

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"


def _require(name: str) -> str:
    value = os.getenv(name)
    if value is None or not str(value).strip():
        raise ConfigError(f"Required environment variable missing: {name}")
    return str(value).strip()


def _optional(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None or not str(value).strip():
        return default
    return str(value).strip()


def _parse_csv(value: str) -> List[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def _parse_optional_positive_int(value: str) -> Optional[int]:
    """0 or empty means no limit."""
    raw = (value or "").strip()
    if not raw or raw == "0":
        return None
    parsed = int(raw)
    return parsed if parsed > 0 else None


@dataclass(frozen=True)
class Settings:
    """Typed configuration object."""

    kafka_bootstrap_servers: str
    kafka_topic_shop: str
    kafka_topic_cosmetics: str
    kafka_topic_islands: str
    kafka_topic_island_metrics: str
    kafka_topic_ingestion_status: str

    minio_profile: str
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str
    minio_secure: bool

    telegram_bot_token: str
    duckdb_path: str
    gold_data_root: str
    duckdb_gold_read_mode: str

    fortnite_api_base_url: str
    fortnite_api_key: str
    fortnite_cosmetics_kafka_chunk_size: int
    fortnite_ecosystem_api_base_url: str
    fortnite_client_id: str
    fortnite_client_secret: str
    fortnite_ecosystem_metric_interval: str
    fortnite_ecosystem_island_page_size: int
    fortnite_ecosystem_max_island_pages: int
    fortnite_ecosystem_catalog_max_pages: int
    fortnite_ecosystem_catalog_page_delay_seconds: float
    fortnite_ecosystem_metrics_delay_seconds: float
    fortnite_ecosystem_demo_island_code: str
    fortnite_ecosystem_default_metrics: List[str]
    fortnite_max_islands: Optional[int]
    fortnite_max_messages_per_topic: int

    log_level: str
    request_timeout_seconds: int
    request_retry_count: int

    @property
    def minio_health_url(self) -> str:
        """Build MinIO liveness URL from configured endpoint."""
        endpoint = self.minio_endpoint.rstrip("/")
        if not endpoint.startswith("http"):
            scheme = "https" if self.minio_secure else "http"
            endpoint = f"{scheme}://{endpoint}"
        return f"{endpoint}/minio/health/live"


def _load_env() -> None:
    if _ENV_FILE.is_file():
        load_dotenv(_ENV_FILE)


def load_settings(*, reload: bool = False) -> Settings:
    """Load and validate settings from environment."""
    if reload:
        get_settings.cache_clear()
    return get_settings()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached validated settings (fail fast on first access)."""
    _load_env()

    settings = Settings(
        kafka_bootstrap_servers=_require("KAFKA_BOOTSTRAP_SERVERS"),
        kafka_topic_shop=_optional("KAFKA_TOPIC_SHOP", "fortnite.raw.shop"),
        kafka_topic_cosmetics=_optional(
            "KAFKA_TOPIC_COSMETICS", "fortnite.raw.cosmetics"
        ),
        kafka_topic_islands=_optional("KAFKA_TOPIC_ISLANDS", "fortnite.raw.islands"),
        kafka_topic_island_metrics=_optional(
            "KAFKA_TOPIC_ISLAND_METRICS", "fortnite.raw.island_metrics"
        ),
        kafka_topic_ingestion_status=_optional(
            "KAFKA_TOPIC_INGESTION_STATUS", "fortnite.ops.ingestion_status"
        ),
        minio_profile=_require("MINIO_PROFILE"),
        minio_endpoint=_require("MINIO_ENDPOINT"),
        minio_access_key=_require("MINIO_ACCESS_KEY"),
        minio_secret_key=_require("MINIO_SECRET_KEY"),
        minio_bucket=_require("MINIO_BUCKET"),
        minio_secure=parse_bool(os.getenv("MINIO_SECURE"), default=False),
        telegram_bot_token=_require("TELEGRAM_BOT_TOKEN"),
        duckdb_path=_optional("DUCKDB_PATH", str(_PROJECT_ROOT / "data" / "serving.duckdb")),
        gold_data_root=_optional("GOLD_DATA_ROOT", str(_PROJECT_ROOT / "data" / "gold")),
        duckdb_gold_read_mode=_optional("DUCKDB_GOLD_READ_MODE", "direct_minio").lower(),
        fortnite_api_base_url=_optional("FORTNITE_API_BASE_URL", "https://fortnite-api.com"),
        fortnite_api_key=_optional("FORTNITE_API_KEY", ""),
        fortnite_cosmetics_kafka_chunk_size=int(
            _optional("FORTNITE_COSMETICS_KAFKA_CHUNK_SIZE", "400")
        ),
        fortnite_ecosystem_api_base_url=_optional(
            "FORTNITE_ECOSYSTEM_API_BASE_URL", "https://api.fortnite.com/ecosystem/v1"
        ),
        fortnite_client_id=_optional("FORTNITE_CLIENT_ID", ""),
        fortnite_client_secret=_optional("FORTNITE_CLIENT_SECRET", ""),
        fortnite_ecosystem_metric_interval=_optional(
            "FORTNITE_ECOSYSTEM_METRIC_INTERVAL", "minute"
        ),
        fortnite_ecosystem_island_page_size=int(
            _optional("FORTNITE_ECOSYSTEM_ISLAND_PAGE_SIZE", "100")
        ),
        fortnite_ecosystem_max_island_pages=int(
            _optional("FORTNITE_ECOSYSTEM_MAX_ISLAND_PAGES", "15")
        ),
        fortnite_ecosystem_catalog_max_pages=int(
            _optional("FORTNITE_ECOSYSTEM_CATALOG_MAX_PAGES", "50")
        ),
        fortnite_ecosystem_catalog_page_delay_seconds=float(
            _optional("FORTNITE_ECOSYSTEM_CATALOG_PAGE_DELAY_SECONDS", "0.05")
        ),
        fortnite_ecosystem_metrics_delay_seconds=float(
            _optional("FORTNITE_ECOSYSTEM_METRICS_DELAY_SECONDS", "0.15")
        ),
        fortnite_ecosystem_demo_island_code=_optional(
            "FORTNITE_ECOSYSTEM_DEMO_ISLAND_CODE", ""
        ),
        fortnite_ecosystem_default_metrics=_parse_csv(
            _optional(
                "FORTNITE_ECOSYSTEM_DEFAULT_METRICS",
                "peakCCU,uniquePlayers,plays,minutesPlayed",
            )
        ),
        fortnite_max_islands=_parse_optional_positive_int(
            _optional("FORTNITE_MAX_ISLANDS", "0")
        ),
        fortnite_max_messages_per_topic=int(
            _optional("FORTNITE_MAX_MESSAGES_PER_TOPIC", "5000")
        ),
        log_level=_optional("LOG_LEVEL", "INFO"),
        request_timeout_seconds=int(_optional("REQUEST_TIMEOUT_SECONDS", "30")),
        request_retry_count=int(_optional("REQUEST_RETRY_COUNT", "3")),
    )

    validate_minio_config(
        {
            "minio_profile": settings.minio_profile,
            "minio_endpoint": settings.minio_endpoint,
            "minio_access_key": settings.minio_access_key,
            "minio_secret_key": settings.minio_secret_key,
            "minio_bucket": settings.minio_bucket,
            "minio_secure": settings.minio_secure,
        }
    )
    return settings
