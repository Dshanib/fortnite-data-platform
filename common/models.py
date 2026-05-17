"""Typed data models for ingestion, storage, and serving."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def utc_now_iso() -> str:
    """Return current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


@dataclass
class IngestionMetadata:
    """Metadata envelope for every ingested event."""

    source: str
    entity: str
    ingested_at: str
    correlation_id: str
    version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RawEvent:
    """Kafka-bound raw event with metadata and payload."""

    metadata: IngestionMetadata
    payload: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {"metadata": self.metadata.to_dict(), "payload": self.payload}


@dataclass
class CcuPayload:
    """Concurrent users snapshot."""

    player_count: int
    captured_at: str
    source_url: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ShopPayload:
    """Item shop snapshot."""

    items: List[Dict[str, Any]]
    captured_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CosmeticsPayload:
    """Cosmetics catalog snapshot."""

    cosmetics: List[Dict[str, Any]]
    captured_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SourceHealthEvent:
    """Operational health signal for ingestion pipelines."""

    source: str
    entity: str
    status: str
    message: str
    observed_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class QueryResponse:
    """Structured response from the serving layer."""

    query_name: str
    success: bool
    data: Optional[Any] = None
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
