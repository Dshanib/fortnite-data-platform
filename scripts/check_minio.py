#!/usr/bin/env python3
"""MinIO connectivity and health check script."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts._script_runtime import bootstrap, safe_print

bootstrap()

from common.logging import configure_logging, get_logger
from config.settings import get_settings
from storage.healthcheck import check_minio_live, ensure_minio_ready

logger = get_logger(__name__)


def main() -> int:
    """Validate MinIO liveness URL and bucket connectivity."""
    settings = get_settings()
    configure_logging(settings.log_level)

    if not check_minio_live(settings):
        safe_print(f"MinIO health check failed: {settings.minio_health_url}")
        return 1

    ensure_minio_ready(settings)

    safe_print(f"MinIO health: OK ({settings.minio_health_url})")
    safe_print(f"MinIO profile: {settings.minio_profile}")
    safe_print(f"MinIO endpoint: {settings.minio_endpoint}")
    safe_print(f"MinIO bucket: {settings.minio_bucket}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
