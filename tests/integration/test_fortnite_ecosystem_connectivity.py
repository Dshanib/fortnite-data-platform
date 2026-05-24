"""Live connectivity check for the Fortnite Ecosystem API."""

from __future__ import annotations

import pytest

from common.exceptions import ApiClientError
from common.logging import configure_logging, get_logger
from config.settings import get_settings
from ingestion.clients.ecosystem_api_client import EcosystemApiClient

logger = get_logger(__name__)

pytestmark = pytest.mark.integration


def _status_message(exc: ApiClientError) -> str:
    if exc.status_code == 401:
        return "401 Unauthorized — authentication required"
    if exc.status_code == 403:
        return "403 Forbidden — authentication required or insufficient scope"
    if exc.status_code == 404:
        return "404 Not Found — island or metric unavailable"
    if exc.status_code == 429:
        return "429 Too Many Requests — rate limit exceeded"
    return str(exc)


@pytest.mark.integration
def test_fortnite_ecosystem_islands_and_metrics_reachable() -> None:
    """GET /islands and metrics for the first island."""
    settings = get_settings()
    configure_logging(settings.log_level)
    client = EcosystemApiClient(settings)
    client.authenticate()
    islands_response = client.list_islands()
    islands = islands_response.get("data") or []
    assert isinstance(islands, list)
    print(f"GET /islands: ok, count={len(islands)}")
    if not islands:
        return
    first = islands[0]
    code = str(first.get("code") or first.get("displayName") or "")
    assert code, "first island missing code"
    interval = settings.fortnite_ecosystem_metric_interval
    try:
        metrics = client.get_metrics_bundle(code, interval=interval)
        print(f"GET /islands/{{code}}/metrics/{interval}: ok, keys={list(metrics.keys())}")
    except ApiClientError as exc:
        pytest.skip(_status_message(exc))


def main() -> int:
    try:
        test_fortnite_ecosystem_islands_and_metrics_reachable()
        print("\nFortnite Ecosystem API: reachable")
        return 0
    except ApiClientError as exc:
        print(f"\nFortnite Ecosystem API: FAILED — {_status_message(exc)}")
        return 1
    except Exception as exc:
        logger.error("Ecosystem API check failed: %s", exc)
        print(f"\nFortnite Ecosystem API: FAILED — {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
