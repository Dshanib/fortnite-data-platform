#!/usr/bin/env python3
"""Validate connectivity to the Fortnite Ecosystem API."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

from common.exceptions import ApiClientError
from common.logging import configure_logging, get_logger
from config.settings import get_settings

load_dotenv(_ROOT / ".env")

import os

_MINIMAL_ENV = {
    "KAFKA_BOOTSTRAP_SERVERS": "localhost:9092",
    "MINIO_PROFILE": "internal",
    "MINIO_ENDPOINT": "http://localhost:9000",
    "MINIO_ACCESS_KEY": "x",
    "MINIO_SECRET_KEY": "x",
    "MINIO_BUCKET": "fortnite-data",
    "TELEGRAM_BOT_TOKEN": "test",
}
for _key, _value in _MINIMAL_ENV.items():
    os.environ.setdefault(_key, _value)

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
        print("\nGET /islands")
        print("  status: ok")
        print(f"  count: {len(islands)}")
        if islands:
            first = islands[0]
            print(f"  first island code: {first.get('code')}")
            print(f"  first island title: {first.get('title')}")

            code = str(first.get("code") or first.get("displayName") or "")
            interval = settings.fortnite_ecosystem_metric_interval
            if code:
                print(f"\nGET /islands/{{code}}/metrics/{interval} (first island)")
                try:
                    metrics = client.get_metrics_bundle(code, interval=interval)
                    print("  status: ok")
                    print(f"  metric keys: {list(metrics.keys())}")
                except ApiClientError as exc:
                    print(f"  metrics call: {_status_message(exc)}")
        else:
            print("  no islands returned")

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
    sys.exit(main())
