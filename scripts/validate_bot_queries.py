#!/usr/bin/env python3
"""Simulate bot menu queries against QueryService (no Telegram network)."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts._script_runtime import bootstrap, safe_print

bootstrap()

from bot.formatters import format_menu_response
from bot.handlers import BotHandlers
from bot.intents import Intent, MenuAction
from config.settings import get_settings
from serving.query_service import QueryService


def _check_text(name: str, text: str) -> bool:
    bad = ("None", "Traceback", "{", "[{")
    for token in bad:
        if token in text:
            safe_print(f"  FAIL {name}: contains {token!r}")
            return False
    if not text.strip():
        safe_print(f"  FAIL {name}: empty output")
        return False
    safe_print(f"  OK {name} ({len(text)} chars)")
    return True


def main() -> int:
    settings = get_settings()
    service = QueryService(settings, auto_init=True)
    handlers = BotHandlers(service)

    failures = 0

    safe_print("\n=== Menu actions ===")
    for action in (
        MenuAction.CURRENT_ACTIVITY,
        MenuAction.TOP_ISLANDS,
        MenuAction.SHOP_SUMMARY,
        MenuAction.SOURCE_HEALTH,
        MenuAction.ANOMALIES,
        MenuAction.HELP,
    ):
        if action == MenuAction.HELP:
            from bot.formatters import help_text

            text = help_text()
        else:
            response = handlers._run_menu_action(action)
            text = format_menu_response(response)
        if not _check_text(action.value, text):
            failures += 1

    safe_print("\n=== Intent fallbacks ===")
    for intent in (
        Intent.CURRENT_CCU,
        Intent.TOP_ISLANDS,
        Intent.SHOP_SUMMARY,
        Intent.SOURCE_HEALTH,
        Intent.ANOMALY_CHECK,
        Intent.AVG_CCU_TODAY,
    ):
        response = handlers._dispatch_intent(intent)
        text = format_menu_response(response)
        if not _check_text(intent.value, text):
            failures += 1

    safe_print(f"\nBot query validation: {'SUCCESS' if failures == 0 else 'FAILED'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
