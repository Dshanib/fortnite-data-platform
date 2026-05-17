"""MinIO health check utilities."""

from __future__ import annotations

from typing import Optional

import requests

from common.logging import get_logger
from config.settings import Settings, get_settings

logger = get_logger(__name__)


def check_minio_live(settings: Optional[Settings] = None) -> bool:
    """Validate MinIO liveness endpoint from configuration."""
    settings = settings or get_settings()
    url = settings.minio_health_url
    try:
        response = requests.get(url, timeout=settings.request_timeout_seconds)
        healthy = response.status_code == 200
        if healthy:
            logger.info("MinIO health OK url=%s", url)
        else:
            logger.warning("MinIO health failed url=%s status=%s", url, response.status_code)
        return healthy
    except requests.RequestException as exc:
        logger.error("MinIO health request failed url=%s: %s", url, exc)
        return False
