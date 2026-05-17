"""Client for Fortnite-API.com (shop and cosmetics reference data)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import requests

from common.exceptions import ApiClientError, IngestionError
from common.logging import get_logger
from config.settings import Settings, get_settings
from ingestion.clients.api_client import ApiClient

logger = get_logger(__name__)


class FortniteApiClient:
    """https://fortnite-api.com — static shop and cosmetics catalog."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        api_client: Optional[ApiClient] = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._api = api_client or ApiClient(self._settings)
        self._base = self._settings.fortnite_api_base_url.rstrip("/")

    def _headers(self) -> Dict[str, str]:
        if self._settings.fortnite_api_key:
            return {"Authorization": self._settings.fortnite_api_key}
        return {}

    def get_shop(self) -> Dict[str, Any]:
        """GET /v2/shop — current item shop snapshot."""
        return self._api.get(f"{self._base}/v2/shop", headers=self._headers())

    def get_shop_entries(self) -> List[Dict[str, Any]]:
        """Return normalized shop entries from the shop API response."""
        data = self.get_shop()
        entries = (
            data.get("data", {}).get("entries")
            or data.get("data", {}).get("featured")
            or data.get("data", {}).get("daily")
            or []
        )
        if not entries and isinstance(data.get("data"), dict):
            entries = [
                value
                for value in data["data"].values()
                if isinstance(value, list) and value
            ]
            entries = entries[0] if entries else []
        if not entries:
            raise IngestionError("Fortnite-API shop response contained no entries")
        return entries

    def get_cosmetics(self) -> Dict[str, Any]:
        """GET /v2/cosmetics/br — full cosmetics catalog."""
        return self._api.get(f"{self._base}/v2/cosmetics/br", headers=self._headers())

    def get_cosmetics_list(self, *, limit: int = 500) -> List[Dict[str, Any]]:
        """Return cosmetics records capped at limit."""
        data = self.get_cosmetics()
        cosmetics = data.get("data") or []
        if isinstance(cosmetics, dict):
            cosmetics = list(cosmetics.values())
        if not cosmetics:
            raise IngestionError("Fortnite-API cosmetics response was empty")
        return cosmetics[:limit]
