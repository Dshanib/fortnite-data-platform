"""Intent detection for Telegram messages."""

from __future__ import annotations

from enum import Enum
from typing import Dict


class Intent(str, Enum):
    CURRENT_CCU = "current_ccu"
    AVG_CCU_TODAY = "avg_ccu_today"
    ANOMALY_CHECK = "anomaly_check"
    SHOP_SUMMARY = "shop_summary"
    SOURCE_HEALTH = "source_health"
    HELP = "help"
    UNKNOWN = "unknown"


_KEYWORDS: Dict[Intent, tuple[str, ...]] = {
    Intent.CURRENT_CCU: ("ccu", "players", "online", "current ccu"),
    Intent.AVG_CCU_TODAY: ("avg", "average", "today"),
    Intent.ANOMALY_CHECK: ("anomaly", "anomalies", "spike"),
    Intent.SHOP_SUMMARY: ("shop", "rarity", "items"),
    Intent.SOURCE_HEALTH: ("health", "status", "sources"),
    Intent.HELP: ("help", "start", "commands"),
}


def detect_intent(text: str) -> Intent:
    """Map user message text to a supported intent."""
    normalized = (text or "").strip().lower()
    if not normalized:
        return Intent.UNKNOWN
    if normalized.startswith("/help"):
        return Intent.HELP
    if normalized.startswith("/start"):
        return Intent.HELP

    for intent, keywords in _KEYWORDS.items():
        if intent == Intent.HELP:
            continue
        if any(keyword in normalized for keyword in keywords):
            return intent
    return Intent.UNKNOWN
