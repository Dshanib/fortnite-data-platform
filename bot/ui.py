"""Telegram UI building blocks (keyboards, layout helpers)."""

from __future__ import annotations

import html
from datetime import datetime
from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from bot.copy_he import (
    BTN_ANOMALIES,
    BTN_CURRENT_ACTIVITY,
    BTN_HELP,
    BTN_HOME,
    BTN_SHOP,
    BTN_TOP_ISLANDS,
)
from bot.intents import MenuAction

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


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Primary menu — user-facing actions, one per row."""
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(BTN_CURRENT_ACTIVITY, callback_data=MenuAction.CURRENT_ACTIVITY.value)],
            [InlineKeyboardButton(BTN_TOP_ISLANDS, callback_data=MenuAction.TOP_ISLANDS.value)],
            [InlineKeyboardButton(BTN_SHOP, callback_data=MenuAction.SHOP_SUMMARY.value)],
            [InlineKeyboardButton(BTN_ANOMALIES, callback_data=MenuAction.ANOMALIES.value)],
            [InlineKeyboardButton(BTN_HELP, callback_data=MenuAction.HELP.value)],
        ]
    )


def back_menu_keyboard() -> InlineKeyboardMarkup:
    """Nav after viewing a result."""
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(BTN_HOME, callback_data=MenuAction.HOME.value)]]
    )
