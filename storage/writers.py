"""Storage writers for bronze layer objects."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from common.logging import get_logger
from config.settings import Settings, get_settings
from storage.minio_client import MinioStorageClient
from storage.paths import LAYER_BRONZE, build_object_key

logger = get_logger(__name__)


class BronzeWriter:
    """Write raw JSON events to MinIO bronze paths."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        client: Optional[MinioStorageClient] = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._client = client or MinioStorageClient(self._settings)

    def write_entity_event(
        self,
        entity: str,
        event: Dict[str, Any],
        *,
        filename: Optional[str] = None,
    ) -> str:
        """Serialize event to JSON and upload to bronze layer."""
        name = filename or f"{entity}.json"
        key = build_object_key(LAYER_BRONZE, entity, filename=name)
        payload = json.dumps(event, default=str).encode("utf-8")
        self._client.ensure_bucket()
        self._client.put_bytes(key, payload)
        logger.info("Bronze write complete entity=%s key=%s", entity, key)
        return key
