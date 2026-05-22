"""Telegram formatter tests (Hebrew UI)."""

from __future__ import annotations

from common.models import QueryResponse
from bot.formatters import (
    format_anomalies,
    format_current_activity,
    format_no_data,
    format_top_islands,
    help_text,
    main_menu_keyboard,
    welcome_text,
)
from bot.intents import MenuAction


def test_welcome_text_hebrew() -> None:
    text = welcome_text()
    assert "שלום" in text
    assert "מרכז הנתונים" in text
    assert "Gold" not in text
    assert "<b>" in text


def test_format_no_data_hebrew() -> None:
    response = QueryResponse(
        query_name="get_recent_anomalies",
        success=False,
        status="no_data",
        data=[],
        message="אין מערך חריגות",
    )
    text = format_no_data(response)
    assert "אין נתונים" in text
    assert "אין מערך חריגות" in text


def test_format_current_activity_hebrew() -> None:
    response = QueryResponse(
        query_name="get_current_ccu",
        success=True,
        status="ok",
        data=[
            {
                "island_code": "A",
                "title": "אי בדיקה",
                "peak_ccu": 42.0,
                "total_peak_ccu": 100.0,
                "latest_metric_timestamp": "2026-05-17T12:00:00Z",
            }
        ],
    )
    text = format_current_activity(response)
    assert "אי בדיקה" in text
    assert "42" in text
    assert "שחקנים מחוברים" in text


def test_format_top_islands_hebrew() -> None:
    response = QueryResponse(
        query_name="get_top_islands",
        success=True,
        status="ok",
        data=[
            {"rank": 1, "island_code": "A", "title": "ראשון", "peak_ccu": 10, "unique_players": 5},
            {"rank": 2, "island_code": "B", "title": "שני", "peak_ccu": 3, "unique_players": 2},
        ],
    )
    text = format_top_islands(response)
    assert "#1" in text
    assert "ראשון" in text
    assert "פופולריים" in text


def test_format_anomalies_hebrew() -> None:
    response = QueryResponse(
        query_name="get_recent_anomalies",
        success=True,
        status="ok",
        data=[
            {
                "island_code": "A",
                "title": "אי חריג",
                "peak_ccu": 100.0,
                "severity": "high",
                "metric_timestamp": "2026-05-17T12:00:00Z",
                "pct_change_from_previous": 1.0,
            }
        ],
    )
    text = format_anomalies(response)
    assert "חריגות" in text
    assert "אי חריג" in text
    assert "100" in text


def test_main_menu_has_primary_actions() -> None:
    keyboard = main_menu_keyboard()
    callbacks = [
        btn.callback_data
        for row in keyboard.inline_keyboard
        for btn in row
    ]
    assert MenuAction.CURRENT_ACTIVITY.value in callbacks
    assert MenuAction.ANOMALIES.value in callbacks
    assert MenuAction.SOURCE_HEALTH.value not in callbacks
    assert len(callbacks) == 5


def test_help_text_hebrew() -> None:
    text = help_text()
    assert "איך משתמשים" in text
    assert "בריאות" not in text
