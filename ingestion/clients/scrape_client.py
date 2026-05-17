"""DEPRECATED: Web scraping is not part of the primary ingestion architecture.

Retained only as an optional legacy fallback. Do not use in new pipelines.
Primary data sources:
  - https://fortnite-api.com (shop, cosmetics)
  - https://api.fortnite.com/ecosystem/v1 (islands, metrics)
"""

from __future__ import annotations

import time
import warnings
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

from common.exceptions import ScrapeClientError
from common.logging import get_logger
from config.settings import Settings, get_settings

logger = get_logger(__name__)


class ScrapeClient:
    """Legacy HTML scraper — deprecated, not used by main ingestion flow."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        warnings.warn(
            "ScrapeClient is deprecated; use Fortnite API clients instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self._settings = settings or get_settings()
        self._session = requests.Session()

    def fetch_html(self, url: str) -> str:
        """Fetch raw HTML from URL with retries."""
        last_error: Optional[Exception] = None
        retries = max(1, self._settings.request_retry_count)

        for attempt in range(1, retries + 1):
            try:
                response = self._session.get(
                    url, timeout=self._settings.request_timeout_seconds
                )
                response.raise_for_status()
                return response.text
            except requests.RequestException as exc:
                last_error = exc
                logger.warning(
                    "Scrape fetch failed url=%s attempt=%s/%s: %s",
                    url,
                    attempt,
                    retries,
                    exc,
                )
                if attempt < retries:
                    time.sleep(min(2 ** (attempt - 1), 8))

        raise ScrapeClientError(f"Failed to fetch {url}") from last_error

    def extract_text_by_selectors(
        self,
        html: str,
        selectors: List[str],
    ) -> List[str]:
        """Extract text nodes matching CSS selectors."""
        soup = BeautifulSoup(html, "html.parser")
        results: List[str] = []
        for selector in selectors:
            try:
                for element in soup.select(selector):
                    text = element.get_text(strip=True)
                    if text:
                        results.append(text)
            except Exception as exc:
                logger.warning("Selector parse failed selector=%s: %s", selector, exc)
        return results
