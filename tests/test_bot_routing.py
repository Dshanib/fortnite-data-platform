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
