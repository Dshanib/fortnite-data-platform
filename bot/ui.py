"""Telegram UI building blocks (keyboards, layout helpers)."""

from __future__ import annotations

import html
from datetime import datetime
from typing import Any, Dict, List, Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from bot.copy_he import (
    BTN_ANOMALIES,
    BTN_ACTIVITY_HUB,
    BTN_BACK_SHOP,
    BTN_HELP,
    BTN_HOME,
    BTN_MOST_ACTIVE_ISLAND,
    BTN_PLAYERS_NOW,
    BTN_SHOP,
    BTN_TOP_ISLANDS,
    CATEGORY_LABELS,
)
from bot.intents import SHOP_CATEGORY_PREFIX, MenuAction

_DIVIDER = "━━━━━━━━━━━━━━━━"


def esc(value: Any) -> str:
    """Escape dynamic text for Telegram HTML."""
    if value is None:
        return "—"
    return html.escape(str(value), quote=False)


def divider() -> str:
    return _DIVIDER


def screen_header(title: str, subtitle: str = "") -> str:
    lines = [f"<b>{esc(title)}</b>"]
    if subtitle:
        lines.append(f"<i>{esc(subtitle)}</i>")
    lines.append(_DIVIDER)
    return "\n".join(lines)


def format_timestamp(value: Any) -> str:
    """Short Hebrew-friendly timestamp from ISO strings."""
    if value is None:
        return "—"
    raw = str(value).strip()
    if not raw:
        return "—"
    try:
        normalized = raw.replace("Z", "+00:00")
        if " " in normalized and "T" not in normalized:
            normalized = normalized.replace(" ", "T", 1)
        dt = datetime.fromisoformat(normalized)
        return dt.strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return esc(raw[:19])


def format_number(value: Any, *, decimals: int = 0) -> str:
    if value is None:
        return "—"
    try:
        num = float(value)
        if decimals == 0:
            return esc(f"{int(num):,}")
        return esc(f"{num:,.{decimals}f}")
    except (TypeError, ValueError):
        return esc(value)


def category_label(raw: Any) -> str:
    """Shop section label: cosmetics type if known, else layout_id from shop."""
    key = str(raw or "unknown").strip().lower()
    if key in CATEGORY_LABELS:
        return CATEGORY_LABELS[key]
    if key == "other":
        return "אחר"
    return esc(str(raw or key))


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Primary menu — user-facing actions, one per row."""
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(BTN_ACTIVITY_HUB, callback_data=MenuAction.ACTIVITY_HUB.value)],
            [InlineKeyboardButton(BTN_TOP_ISLANDS, callback_data=MenuAction.TOP_ISLANDS.value)],
            [InlineKeyboardButton(BTN_SHOP, callback_data=MenuAction.SHOP_HUB.value)],
            [InlineKeyboardButton(BTN_ANOMALIES, callback_data=MenuAction.ANOMALIES.value)],
            [InlineKeyboardButton(BTN_HELP, callback_data=MenuAction.HELP.value)],
        ]
    )


def activity_submenu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(BTN_PLAYERS_NOW, callback_data=MenuAction.PLAYERS_NOW.value)],
            [
                InlineKeyboardButton(
                    BTN_MOST_ACTIVE_ISLAND,
                    callback_data=MenuAction.MOST_ACTIVE_ISLAND.value,
                )
            ],
            [InlineKeyboardButton(BTN_HOME, callback_data=MenuAction.HOME.value)],
        ]
    )


def shop_category_keyboard(categories: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """One button per shop category; callback menu:shop:<category>."""
    rows: List[List[InlineKeyboardButton]] = []
    for row in categories[:12]:
        cat = str(row.get("category") or "unknown").strip()
        count = row.get("item_count", 0)
        label = f"{category_label(cat)} ({int(count)})"
        rows.append(
            [
                InlineKeyboardButton(
                    label,
                    callback_data=f"{SHOP_CATEGORY_PREFIX}{cat}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(BTN_HOME, callback_data=MenuAction.HOME.value)])
    return InlineKeyboardMarkup(rows)


def back_menu_keyboard() -> InlineKeyboardMarkup:
    """Nav after viewing a result."""
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(BTN_HOME, callback_data=MenuAction.HOME.value)]]
    )


def shop_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(BTN_BACK_SHOP, callback_data=MenuAction.SHOP_HUB.value)],
            [InlineKeyboardButton(BTN_HOME, callback_data=MenuAction.HOME.value)],
        ]
    )
