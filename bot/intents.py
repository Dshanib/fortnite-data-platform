"""Intent detection and menu callback constants for Telegram."""

from __future__ import annotations

from enum import Enum
from typing import Dict, Optional, Tuple

SHOP_CATEGORY_PREFIX = "menu:shop:"


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
    ACTIVITY_HUB = "menu:activity_hub"
    PLAYERS_NOW = "menu:players_now"
    MOST_ACTIVE_ISLAND = "menu:most_active_island"
    TOP_ISLANDS = "menu:top_islands"
    SHOP_HUB = "menu:shop_hub"
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
        "איים פעילים",
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


def parse_menu_callback(callback_data: str) -> Tuple[Optional[MenuAction], Optional[str]]:
    """
    Parse callback_data into a menu action and optional payload (e.g. shop category).
    """
    data = (callback_data or "").strip()
    if not data:
        return None, None
    if data.startswith(SHOP_CATEGORY_PREFIX):
        return None, data[len(SHOP_CATEGORY_PREFIX) :]
    try:
        return MenuAction(data), None
    except ValueError:
        return None, None


def menu_action_for_callback(callback_data: str) -> Optional[MenuAction]:
    """Parse callback_data into a menu action, if recognized."""
    action, payload = parse_menu_callback(callback_data)
    if payload is not None:
        return None
    return action
