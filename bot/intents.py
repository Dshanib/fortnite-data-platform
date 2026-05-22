"""Intent detection and menu callback constants for Telegram."""

from __future__ import annotations

from enum import Enum
from typing import Dict, Optional


class Intent(str, Enum):
    CURRENT_CCU = "current_ccu"
    AVG_CCU_TODAY = "avg_ccu_today"
    ANOMALY_CHECK = "anomaly_check"
    SHOP_SUMMARY = "shop_summary"
    SOURCE_HEALTH = "source_health"
    TOP_ISLANDS = "top_islands"
    HELP = "help"
    UNKNOWN = "unknown"


class MenuAction(str, Enum):
    """Inline keyboard callback_data values."""

    HOME = "menu:home"
    CURRENT_ACTIVITY = "menu:current_activity"
    TOP_ISLANDS = "menu:top_islands"
    SHOP_SUMMARY = "menu:shop_summary"
    SOURCE_HEALTH = "menu:source_health"
    ANOMALIES = "menu:anomalies"
    HELP = "menu:help"


_KEYWORDS: Dict[Intent, tuple[str, ...]] = {
    Intent.CURRENT_CCU: (
        "ccu",
        "פעילות",
        "שחקנים",
        "אונליין",
        "מחוברים",
        "activity",
        "players",
    ),
    Intent.AVG_CCU_TODAY: ("avg", "ממוצע", "היום", "today", "average"),
    Intent.ANOMALY_CHECK: ("anomaly", "חריגות", "אנומליה", "anomalies"),
    Intent.SHOP_SUMMARY: ("shop", "חנות", "נדירות", "rarity", "items"),
    Intent.SOURCE_HEALTH: ("health", "בריאות", "סטטוס", "מקורות", "status"),
    Intent.TOP_ISLANDS: (
        "top islands",
        "איים מובילים",
        "דירוג",
        "מובילים",
        "leaderboard",
    ),
    Intent.HELP: ("help", "עזרה", "תפריט", "התחל", "commands"),
}


def detect_intent(text: str) -> Intent:
    """Map user message text to a supported intent (secondary to menu)."""
    normalized = (text or "").strip().lower()
    if not normalized:
        return Intent.UNKNOWN
    if normalized.startswith("/help"):
        return Intent.HELP
    if normalized.startswith("/start") or normalized.startswith("/menu"):
        return Intent.HELP

    for intent, keywords in _KEYWORDS.items():
        if intent == Intent.HELP:
            continue
        if any(keyword in normalized for keyword in keywords):
            return intent
    return Intent.UNKNOWN


def menu_action_for_callback(callback_data: str) -> Optional[MenuAction]:
    """Parse callback_data into a menu action, if recognized."""
    try:
        return MenuAction(callback_data)
    except ValueError:
        return None
