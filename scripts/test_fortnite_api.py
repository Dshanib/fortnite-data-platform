#!/usr/bin/env python3
"""Validate connectivity to Fortnite-API.com."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts._script_runtime import bootstrap, safe_print

bootstrap()

from common.logging import configure_logging, get_logger
from config.settings import get_settings
from ingestion.clients.fortnite_api_client import FortniteApiClient

logger = get_logger(__name__)


def _summarize(name: str, data: Dict[str, Any]) -> None:
    top_keys = list(data.keys())
    records = data.get("data")
    count = len(records) if isinstance(records, list) else "n/a"
    safe_print(f"\n{name}")
    safe_print("  status: ok")
    safe_print(f"  top-level keys: {top_keys}")
    safe_print(f"  record count: {count}")


def main() -> int:
    settings = get_settings()
    configure_logging(settings.log_level)
    client = FortniteApiClient(settings)

    try:
        shop = client.get_shop()
        _summarize("GET /v2/shop", shop)
        cosmetics = client.get_cosmetics()
        _summarize("GET /v2/cosmetics/br", cosmetics)
        safe_print("\nFortnite-API.com: reachable")
        return 0
    except Exception as exc:
        logger.error("Fortnite-API.com check failed: %s", exc)
        safe_print(f"\nFortnite-API.com: FAILED — {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
