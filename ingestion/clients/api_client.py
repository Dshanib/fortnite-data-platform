"""Generic HTTP API client with retries and latency measurement."""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

import requests
from requests import Response

from common.exceptions import ApiClientError
from common.logging import get_logger
from config.settings import Settings, get_settings

logger = get_logger(__name__)


class ApiClient:
    """GET-focused API client with timeout, retry, and backoff."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or get_settings()
        self._session = requests.Session()

    def get(
        self,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Perform GET with retries and return JSON body."""
        last_error: Optional[Exception] = None
        retries = max(1, self._settings.request_retry_count)

        for attempt in range(1, retries + 1):
            started = time.perf_counter()
            try:
                response = self._session.get(
                    url,
                    headers=headers,
                    params=params,
                    timeout=self._settings.request_timeout_seconds,
                )
                elapsed_ms = (time.perf_counter() - started) * 1000
                logger.info(
                    "GET %s status=%s latency_ms=%.1f attempt=%s",
                    url,
                    response.status_code,
                    elapsed_ms,
                    attempt,
                )
                self._raise_for_status(response)
                return response.json()
            except (requests.RequestException, ValueError) as exc:
                last_error = exc
                logger.warning(
                    "GET %s failed attempt=%s/%s: %s", url, attempt, retries, exc
                )
                if attempt < retries:
                    time.sleep(min(2 ** (attempt - 1), 8))

        raise ApiClientError(f"GET failed for {url}") from last_error

    @staticmethod
    def _raise_for_status(response: Response) -> None:
        if response.status_code >= 400:
            raise ApiClientError(
                f"HTTP {response.status_code} for {response.url}: {response.text[:200]}",
                status_code=response.status_code,
            )
