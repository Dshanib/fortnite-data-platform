"""MinIO connectivity and health check script."""

from __future__ import annotations

import sys

from common.logging import configure_logging, get_logger
from config.settings import get_settings
from storage.healthcheck import check_minio_live
from storage.minio_client import MinioStorageClient

logger = get_logger(__name__)


def main() -> int:
    """Validate MinIO liveness URL and bucket connectivity."""
    settings = get_settings()
    configure_logging(settings.log_level)

    if not check_minio_live(settings):
        logger.error("MinIO liveness check failed url=%s", settings.minio_health_url)
        return 1

    client = MinioStorageClient(settings)
    if not client.validate_connectivity():
        logger.warning("Bucket missing; attempting ensure_bucket profile=%s", settings.minio_profile)
        client.ensure_bucket()

    logger.info("MinIO OK profile=%s endpoint=%s bucket=%s", settings.minio_profile, settings.minio_endpoint, settings.minio_bucket)
    return 0


if __name__ == "__main__":
    sys.exit(main())
