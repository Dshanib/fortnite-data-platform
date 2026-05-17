#!/usr/bin/env python3
"""Validate connectivity to Fortnite-API.com."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

from common.logging import configure_logging, get_logger
from config.settings import get_settings

load_dotenv(_ROOT / ".env")

# Minimal defaults so API checks do not require full platform .env
_MINIMAL_ENV = {
    "KAFKA_BOOTSTRAP_SERVERS": "localhost:9092",
    "MINIO_PROFILE": "internal",
    "MINIO_ENDPOINT": "http://localhost:9000",
    "MINIO_ACCESS_KEY": "x",
    "MINIO_SECRET_KEY": "x",
    "MINIO_BUCKET": "fortnite-data",
    "TELEGRAM_BOT_TOKEN": "test",
}
import os

for _key, _value in _MINIMAL_ENV.items():
    os.environ.setdefault(_key, _value)

from ingestion.clients.fortnite_api_client import FortniteApiClient

logger = get_logger(__name__)


def _summarize(name: str, data: Dict[str, Any]) -> None:
    top_keys = list(data.keys())
    records = data.get("data")
    count = len(records) if isinstance(records, list) else "n/a"
    print(f"\n{name}")
    print(f"  status: ok")
    print(f"  top-level keys: {top_keys}")
    print(f"  record count: {count}")


def main() -> int:
    settings = get_settings()
    configure_logging(settings.log_level)
    client = FortniteApiClient(settings)

    try:
        shop = client.get_shop()
        _summarize("GET /v2/shop", shop)
        cosmetics = client.get_cosmetics()
        _summarize("GET /v2/cosmetics/br", cosmetics)
        print("\nFortnite-API.com: reachable")
        return 0
    except Exception as exc:
        logger.error("Fortnite-API.com check failed: %s", exc)
        print(f"\nFortnite-API.com: FAILED — {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
