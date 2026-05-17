"""Client for the official Fortnite Ecosystem API (island engagement metrics)."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import requests

from common.exceptions import ApiClientError, IngestionError
from common.logging import get_logger
from common.models import utc_now_iso
from config.settings import Settings, get_settings
from ingestion.clients.api_client import ApiClient
from ingestion.clients.api_result import ApiFetchResult

logger = get_logger(__name__)

_EPIC_TOKEN_URL = "https://api.epicgames.dev/epic/oauth/v1/token"

_METRIC_PATH_SLUGS = {
    "peakCCU": "peak-ccu",
    "uniquePlayers": "unique-players",
    "plays": "plays",
    "minutesPlayed": "minutes-played",
    "averageMinutesPerPlayer": "average-minutes-per-player",
    "favorites": "favorites",
    "recommendations": "recommendations",
    "retention": "retention",
}


class EcosystemApiClient:
    """https://api.fortnite.com/ecosystem/v1 — islands and engagement metrics."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        api_client: Optional[ApiClient] = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._api = api_client or ApiClient(self._settings)
        self._base = self._settings.fortnite_ecosystem_api_base_url.rstrip("/")
        self._bearer_token: Optional[str] = None

    def _auth_headers(self) -> Dict[str, str]:
        if self._bearer_token:
            return {"Authorization": f"Bearer {self._bearer_token}"}
        return {}

    def authenticate(self) -> None:
        """Obtain OAuth2 token when Epic client credentials are configured."""
        client_id = self._settings.fortnite_client_id
        client_secret = self._settings.fortnite_client_secret
        if not client_id or not client_secret:
            logger.debug("Epic OAuth not configured; calling public Ecosystem endpoints")
            return
        try:
            response = requests.post(
                _EPIC_TOKEN_URL,
                data={"grant_type": "client_credentials"},
                auth=(client_id, client_secret),
                timeout=self._settings.request_timeout_seconds,
            )
            if response.status_code in {401, 403}:
                raise ApiClientError(
                    "Epic OAuth authentication rejected (401/403). "
                    "Verify FORTNITE_CLIENT_ID and FORTNITE_CLIENT_SECRET.",
                    status_code=response.status_code,
                )
            response.raise_for_status()
            token = response.json().get("access_token")
            if not token:
                raise ApiClientError("Epic OAuth response missing access_token")
            self._bearer_token = str(token)
            logger.info("Epic OAuth token acquired for Ecosystem API")
        except requests.RequestException as exc:
            raise ApiClientError("Epic OAuth authentication failed") from exc

    def fetch_islands(self, *, size: Optional[int] = None) -> ApiFetchResult:
        """GET /islands — full response with HTTP metadata."""
        page_size = size or self._settings.fortnite_ecosystem_island_page_size
        try:
            return self._api.get_detailed(
                f"{self._base}/islands",
                headers=self._auth_headers(),
                params={"size": page_size},
            )
        except ApiClientError as exc:
            self._raise_auth_hint(exc)
            raise

    def list_islands(self, *, size: Optional[int] = None) -> Dict[str, Any]:
        """GET /islands — paginated island catalog."""
        return self.fetch_islands(size=size).body

    def list_island_summaries(self, *, size: Optional[int] = None) -> List[Dict[str, Any]]:
        """Return island records from a list response."""
        data = self.list_islands(size=size)
        islands = data.get("data") or []
        if not islands:
            raise IngestionError("Ecosystem API returned no islands")
        return islands

    def get_island(self, island_code: str) -> Dict[str, Any]:
        """GET /islands/{code} — island metadata."""
        code = quote(island_code, safe="")
        try:
            return self._api.get(
                f"{self._base}/islands/{code}",
                headers=self._auth_headers(),
            )
        except ApiClientError as exc:
            self._raise_auth_hint(exc)
            raise

    def fetch_metrics_bundle(
        self,
        island_code: str,
        interval: Optional[str] = None,
        metrics: Optional[List[str]] = None,
    ) -> ApiFetchResult:
        """GET /islands/{code}/metrics/{interval} with HTTP metadata."""
        code = quote(island_code, safe="")
        interval = interval or self._settings.fortnite_ecosystem_metric_interval
        metric_names = metrics or self._settings.fortnite_ecosystem_default_metrics
        params: List[tuple[str, str]] = [("metrics", name) for name in metric_names]
        url = f"{self._base}/islands/{code}/metrics/{interval}"
        try:
            return self._get_with_params(url, params)
        except ApiClientError as exc:
            if exc.status_code == 404:
                return self._fetch_metrics_individually(island_code, interval, metric_names)
            self._raise_auth_hint(exc)
            raise

    def get_metrics_bundle(
        self,
        island_code: str,
        interval: Optional[str] = None,
        metrics: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """GET /islands/{code}/metrics/{interval} with filterable metrics."""
        return self.fetch_metrics_bundle(
            island_code, interval=interval, metrics=metrics
        ).body

    def get_metric_series(
        self,
        island_code: str,
        interval: str,
        metric_name: str,
    ) -> Dict[str, Any]:
        """GET /islands/{code}/metrics/{interval}/{metric-slug}."""
        return self.fetch_metric_series(island_code, interval, metric_name).body

    def _fetch_metrics_individually(
        self,
        island_code: str,
        interval: str,
        metric_names: List[str],
    ) -> ApiFetchResult:
        """Fallback when filterable metrics endpoint is unavailable."""
        started = time.perf_counter()
        bundle: Dict[str, Any] = {}
        status_code = 200
        for name in metric_names:
            try:
                result = self.fetch_metric_series(island_code, interval, name)
                bundle[name] = result.body
                status_code = result.status_code
            except ApiClientError as exc:
                if exc.status_code == 404:
                    logger.warning("Metric unavailable island=%s metric=%s", island_code, name)
                    continue
                raise
        if not bundle:
            raise IngestionError(
                f"No metrics returned for island={island_code} interval={interval}"
            )
        latency_ms = (time.perf_counter() - started) * 1000
        return ApiFetchResult(
            status_code=status_code,
            latency_ms=latency_ms,
            body=bundle,
            fetched_at=utc_now_iso(),
        )

    def fetch_metric_series(
        self,
        island_code: str,
        interval: str,
        metric_name: str,
    ) -> ApiFetchResult:
        """GET /islands/{code}/metrics/{interval}/{metric-slug}."""
        code = quote(island_code, safe="")
        slug = _METRIC_PATH_SLUGS.get(metric_name, metric_name)
        url = f"{self._base}/islands/{code}/metrics/{interval}/{slug}"
        try:
            return self._api.get_detailed(url, headers=self._auth_headers())
        except ApiClientError as exc:
            self._raise_auth_hint(exc)
            raise

    def _get_with_params(self, url: str, params: List[tuple[str, str]]) -> ApiFetchResult:
        """Perform GET with repeated query params (metrics list)."""
        last_error: Optional[Exception] = None
        last_status: Optional[int] = None
        retries = max(1, self._settings.request_retry_count)
        for attempt in range(1, retries + 1):
            started = time.perf_counter()
            try:
                response = self._api._session.get(
                    url,
                    headers=self._auth_headers(),
                    params=params,
                    timeout=self._settings.request_timeout_seconds,
                )
                elapsed_ms = (time.perf_counter() - started) * 1000
                last_status = response.status_code
                logger.info(
                    "GET %s status=%s latency_ms=%.1f attempt=%s",
                    url,
                    response.status_code,
                    elapsed_ms,
                    attempt,
                )
                if response.status_code in {401, 403}:
                    raise ApiClientError(
                        "Ecosystem API authentication required (401/403). "
                        "Configure FORTNITE_CLIENT_ID and FORTNITE_CLIENT_SECRET.",
                        status_code=response.status_code,
                    )
                if response.status_code == 429:
                    raise ApiClientError(
                        "Ecosystem API rate limit exceeded (429). Retry later.",
                        status_code=429,
                    )
                if response.status_code >= 400:
                    raise ApiClientError(
                        f"HTTP {response.status_code}: {response.text[:200]}",
                        status_code=response.status_code,
                    )
                return ApiFetchResult(
                    status_code=response.status_code,
                    latency_ms=elapsed_ms,
                    body=response.json(),
                    fetched_at=utc_now_iso(),
                )
            except ApiClientError:
                raise
            except (requests.RequestException, ValueError) as exc:
                last_error = exc
                if attempt < retries:
                    continue
        raise ApiClientError(f"GET failed for {url}", status_code=last_status) from last_error

    @staticmethod
    def _raise_auth_hint(exc: ApiClientError) -> None:
        if exc.status_code in {401, 403}:
            logger.error(
                "Ecosystem API auth required. Set FORTNITE_CLIENT_ID / "
                "FORTNITE_CLIENT_SECRET in .env (see Epic developer portal)."
            )
