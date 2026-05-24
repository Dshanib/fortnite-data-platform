"""Bot intent routing tests."""

from __future__ import annotations

from bot.intents import Intent, detect_intent


def test_detect_current_ccu() -> None:
    assert detect_intent("what is the current ccu?") == Intent.CURRENT_CCU


def test_detect_shop() -> None:
    assert detect_intent("shop summary") == Intent.SHOP_SUMMARY


def test_detect_unknown() -> None:
    assert detect_intent("random gibberish xyz") == Intent.UNKNOWN


def test_detect_help_command() -> None:
    assert detect_intent("/help") == Intent.HELP


def test_detect_top_islands() -> None:
    assert detect_intent("show top islands") == Intent.TOP_ISLANDS


def test_detect_menu_command() -> None:
    assert detect_intent("/menu") == Intent.HELP


def test_detect_hebrew_shop() -> None:
    assert detect_intent("מה יש בחנות?") == Intent.SHOP_SUMMARY


def test_detect_hebrew_activity() -> None:
    assert detect_intent("כמה שחקנים מחוברים") == Intent.CURRENT_CCU
