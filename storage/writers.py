"""Storage writers for medallion layer objects."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from common.exceptions import StorageError
from common.logging import get_logger
from common.utils import new_correlation_id
from config.settings import Settings, get_settings
from storage.minio_client import MinioStorageClient
from storage.paths import (
    LAYER_BRONZE,
    LAYER_GOLD,
    LAYER_SILVER,
    build_bronze_filename,
    build_bronze_object_key,
    build_object_key,
    parse_event_date,
    resolve_bronze_source,
)

logger = get_logger(__name__)


def write_raw_event_to_bronze(
    event: Dict[str, Any],
    *,
    topic: Optional[str] = None,
    settings: Optional[Settings] = None,
    client: Optional[MinioStorageClient] = None,
) -> str:
    """
    Persist a raw Kafka event envelope to MinIO bronze as UTF-8 JSON.

    Returns the object key (path within bucket).
    """
    writer = BronzeWriter(settings=settings, client=client)
    return writer.write_raw_event_to_bronze(event, topic=topic)


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
        """Serialize event to JSON and upload under the configured layer (legacy paths)."""
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
    """Write raw Kafka ingestion events to MinIO bronze."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        client: Optional[MinioStorageClient] = None,
    ) -> None:
        super().__init__(LAYER_BRONZE, settings=settings, client=client)

    def write_raw_event_to_bronze(
        self,
        event: Dict[str, Any],
        *,
        topic: Optional[str] = None,
    ) -> str:
        """Upload raw event JSON with hive-style bronze partitioning."""
        if not event:
            raise StorageError("Cannot write empty event to bronze")

        try:
            source = resolve_bronze_source(event, topic=topic)
            event_date = parse_event_date(event)
            event_id = str(event.get("event_id") or new_correlation_id())
            event_time = str(
                event.get("event_time")
                or event.get("ingested_at")
                or event.get("observed_at")
                or event_date.isoformat()
            )
            filename = build_bronze_filename(
                source, event_id=event_id, event_time=event_time
            )
            object_key = build_bronze_object_key(
                source, event_date, filename=filename
            )
            payload = json.dumps(event, default=str, ensure_ascii=False).encode("utf-8")
            self._client.ensure_bucket()
            self._client.put_bytes(object_key, payload)
            logger.info(
                "Bronze write complete source=%s key=%s bytes=%s",
                source,
                object_key,
                len(payload),
            )
            return object_key
        except StorageError:
            raise
        except Exception as exc:
            raise StorageError(f"Bronze write failed: {exc}") from exc


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
