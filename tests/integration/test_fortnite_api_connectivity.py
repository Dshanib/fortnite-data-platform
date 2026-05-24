"""Live connectivity check for Fortnite-API.com (shop, cosmetics)."""

from __future__ import annotations

import pytest

from common.logging import configure_logging, get_logger
from config.settings import get_settings
from ingestion.clients.fortnite_api_client import FortniteApiClient

logger = get_logger(__name__)

pytestmark = pytest.mark.integration


def _summarize(name: str, data: dict) -> None:
    records = data.get("data")
    count = len(records) if isinstance(records, list) else "n/a"
    assert "data" in data or records is not None, f"{name}: unexpected response shape"
    print(f"{name}: ok, records={count}")


@pytest.mark.integration
def test_fortnite_api_shop_and_cosmetics_reachable() -> None:
    """GET /v2/shop and /v2/cosmetics/br return data."""
    settings = get_settings()
    configure_logging(settings.log_level)
    client = FortniteApiClient(settings)
    shop = client.get_shop()
    _summarize("GET /v2/shop", shop)
    cosmetics = client.get_cosmetics()
    _summarize("GET /v2/cosmetics/br", cosmetics)


def main() -> int:
    try:
        test_fortnite_api_shop_and_cosmetics_reachable()
        print("\nFortnite-API.com: reachable")
        return 0
    except Exception as exc:
        logger.error("Fortnite-API.com check failed: %s", exc)
        print(f"\nFortnite-API.com: FAILED — {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
