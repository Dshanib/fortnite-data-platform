"""Telegram formatter tests (Hebrew UI)."""

from __future__ import annotations

from common.models import QueryResponse
from bot.formatters import (
    format_anomalies,
    format_most_active_island,
    format_no_data,
    format_players_online,
    format_shop_category_items,
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


def test_format_players_online_hebrew() -> None:
    response = QueryResponse(
        query_name="get_players_online_summary",
        success=True,
        status="ok",
        data=[
            {
                "metric_date": "2026-05-24",
                "active_players_today": 500.0,
                "unique_players_today": 500.0,
                "peak_ccu_today": 128.0,
                "plays_today": 1200.0,
                "islands_with_data": 14,
                "hours_with_data": 8,
                "is_calendar_today": True,
                "data_as_of": "2026-05-24T12:00:00Z",
            }
        ],
    )
    text = format_players_online(response)
    assert "500" in text
    assert "שחקנים פעילים" in text
    assert "1,200" in text or "1200" in text
    assert "Gold" not in text


def test_format_most_active_island_hebrew() -> None:
    response = QueryResponse(
        query_name="get_most_active_island",
        success=True,
        status="ok",
        data=[
            {
                "island_code": "A",
                "title": "אי בדיקה",
                "peak_ccu": 42.0,
                "unique_players": 30.0,
                "plays": 5.0,
                "minutes_played": 100.0,
                "latest_metric_timestamp": "2026-05-24T12:00:00Z",
                "data_as_of": "2026-05-24T12:00:00Z",
            }
        ],
    )
    text = format_most_active_island(response)
    assert "אי בדיקה" in text
    assert "42" in text
    assert "הכי פעיל" in text


def test_format_shop_category_items_hebrew() -> None:
    response = QueryResponse(
        query_name="get_shop_items_by_category",
        success=True,
        status="ok",
        data=[
            {
                "item_name": "סקין בדיקה",
                "rarity": "epic",
                "final_price": 1500,
                "regular_price": 2000,
                "snapshot_date": "2026-05-24",
                "category": "outfit",
            }
        ],
    )
    text = format_shop_category_items(response, category="outfit")
    assert "סקין בדיקה" in text
    assert "אפיק" in text
    assert "1,500" in text or "1500" in text


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
    assert "פעילים" in text or "איים" in text


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
    assert "גבוהה" in text
    assert "100" in text


def test_main_menu_has_primary_actions() -> None:
    keyboard = main_menu_keyboard()
    callbacks = [
        btn.callback_data
        for row in keyboard.inline_keyboard
        for btn in row
    ]
    assert MenuAction.ACTIVITY_HUB.value in callbacks
    assert MenuAction.SHOP_HUB.value in callbacks
    assert MenuAction.ANOMALIES.value in callbacks
    assert len(callbacks) == 5


def test_help_text_hebrew() -> None:
    text = help_text()
    assert "איך משתמשים" in text
    assert "בריאות" not in text
