"""Storage writers for medallion layer objects."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from common.logging import get_logger
from config.settings import Settings, get_settings
from storage.minio_client import MinioStorageClient
from storage.paths import (
    LAYER_BRONZE,
    LAYER_GOLD,
    LAYER_SILVER,
    build_object_key,
)

logger = get_logger(__name__)


class LayerWriter:
    """Write JSON events to MinIO under bronze, silver, or gold prefixes."""

    def __init__(
        self,
        layer: str,
        settings: Optional[Settings] = None,
        client: Optional[MinioStorageClient] = None,
    ) -> None:
        self._layer = layer
        self._settings = settings or get_settings()
        self._client = client or MinioStorageClient(self._settings)

    @property
    def layer(self) -> str:
        return self._layer

    def write_entity_event(
        self,
        entity: str,
        event: Dict[str, Any],
        *,
        filename: Optional[str] = None,
    ) -> str:
        """Serialize event to JSON and upload under the configured layer."""
        name = filename or f"{entity}.json"
        key = build_object_key(self._layer, entity, filename=name)
        payload = json.dumps(event, default=str).encode("utf-8")
        self._client.ensure_bucket()
        self._client.put_bytes(key, payload)
        logger.info(
            "Layer write complete layer=%s entity=%s key=%s",
            self._layer,
            entity,
            key,
        )
        return key


class BronzeWriter(LayerWriter):
    """Write raw JSON events to MinIO bronze paths."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        client: Optional[MinioStorageClient] = None,
    ) -> None:
        super().__init__(LAYER_BRONZE, settings=settings, client=client)


class SilverWriter(LayerWriter):
    """Write cleaned JSON events to MinIO silver paths."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        client: Optional[MinioStorageClient] = None,
    ) -> None:
        super().__init__(LAYER_SILVER, settings=settings, client=client)


class GoldWriter(LayerWriter):
    """Write aggregated JSON artifacts to MinIO gold paths."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        client: Optional[MinioStorageClient] = None,
    ) -> None:
        super().__init__(LAYER_GOLD, settings=settings, client=client)
