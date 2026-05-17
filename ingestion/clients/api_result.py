"""HTTP fetch result with timing metadata for ingestion envelopes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class ApiFetchResult:
    """JSON API response plus request metadata."""

    status_code: int
    latency_ms: float
    body: Dict[str, Any]
    fetched_at: str

    @property
    def request_status(self) -> str:
        return "success" if 200 <= self.status_code < 300 else "failed"
