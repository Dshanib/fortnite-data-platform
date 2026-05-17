#!/usr/bin/env python3
"""Validate connectivity to the Fortnite Ecosystem API."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts._script_runtime import bootstrap, safe_print

bootstrap()

from common.exceptions import ApiClientError
from common.logging import configure_logging, get_logger
from config.settings import get_settings
from ingestion.clients.ecosystem_api_client import EcosystemApiClient

logger = get_logger(__name__)


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


def main() -> int:
    settings = get_settings()
    configure_logging(settings.log_level)
    client = EcosystemApiClient(settings)

    try:
        client.authenticate()
        islands_response = client.list_islands()
        islands = islands_response.get("data") or []
        safe_print("\nGET /islands")
        safe_print("  status: ok")
        safe_print(f"  count: {len(islands)}")
        if islands:
            first = islands[0]
            safe_print(f"  first island code: {first.get('code')}")
            safe_print(f"  first island title: {first.get('title')}")

            code = str(first.get("code") or first.get("displayName") or "")
            interval = settings.fortnite_ecosystem_metric_interval
            if code:
                safe_print(f"\nGET /islands/{{code}}/metrics/{interval} (first island)")
                try:
                    metrics = client.get_metrics_bundle(code, interval=interval)
                    safe_print("  status: ok")
                    safe_print(f"  metric keys: {list(metrics.keys())}")
                except ApiClientError as exc:
                    safe_print(f"  metrics call: {_status_message(exc)}")
        else:
            safe_print("  no islands returned")

        safe_print("\nFortnite Ecosystem API: reachable")
        return 0
    except ApiClientError as exc:
        safe_print(f"\nFortnite Ecosystem API: FAILED — {_status_message(exc)}")
        return 1
    except Exception as exc:
        logger.error("Ecosystem API check failed: %s", exc)
        safe_print(f"\nFortnite Ecosystem API: FAILED — {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
