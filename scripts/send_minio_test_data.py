#!/usr/bin/env python3
"""Upload sample JSON objects to bronze, silver, and gold MinIO prefixes."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts._script_runtime import bootstrap, safe_print

bootstrap()

from common.exceptions import StorageError
from common.logging import configure_logging, get_logger
from common.models import utc_now_iso
from config.settings import get_settings
from storage.healthcheck import check_minio_live
from storage.paths import LAYER_BRONZE, LAYER_GOLD, LAYER_SILVER
from storage.writers import LayerWriter

logger = get_logger(__name__)

_LAYERS = (LAYER_BRONZE, LAYER_SILVER, LAYER_GOLD)


def main() -> int:
    """Write one connectivity test object per medallion layer."""
    try:
        settings = get_settings()
        configure_logging(settings.log_level)

        safe_print(f"MinIO endpoint: {settings.minio_endpoint}")
        safe_print(f"Bucket: {settings.minio_bucket}")

        if not check_minio_live(settings):
            safe_print("MinIO health check failed. Is the server running?")
            safe_print("  docker compose --env-file .env up -d minio")
            return 1

        timestamp = utc_now_iso()
        written: list[str] = []

        for layer in _LAYERS:
            writer = LayerWriter(layer, settings=settings)
            key = writer.write_entity_event(
                "connectivity",
                {
                    "source": "send_minio_test_data",
                    "layer": layer,
                    "status": "success",
                    "message": f"sample write to {layer}",
                    "observed_at": timestamp,
                },
                filename=f"connectivity-{layer}.json",
            )
            written.append(key)
            safe_print(f"  {layer}: uploaded s3://{settings.minio_bucket}/{key}")

        safe_print(f"MinIO upload: SUCCESS ({len(written)} objects)")
        return 0
    except StorageError as exc:
        safe_print(f"MinIO upload: FAILED — {exc}")
        return 1
    except Exception as exc:
        safe_print(f"MinIO upload: FAILED — {exc}")
        logger.exception("send_minio_test_data failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
