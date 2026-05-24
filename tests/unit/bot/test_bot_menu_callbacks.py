"""Menu callback routing tests."""

from __future__ import annotations

from unittest.mock import MagicMock

from bot.handlers import BotHandlers
from bot.intents import MenuAction, menu_action_for_callback, parse_menu_callback
from common.models import QueryResponse


def test_menu_callback_constants() -> None:
    assert menu_action_for_callback("menu:activity_hub") == MenuAction.ACTIVITY_HUB
    assert menu_action_for_callback("menu:players_now") == MenuAction.PLAYERS_NOW
    assert menu_action_for_callback("menu:top_islands") == MenuAction.TOP_ISLANDS
    assert menu_action_for_callback("invalid") is None


def test_parse_shop_category_callback() -> None:
    action, category = parse_menu_callback("menu:shop:outfit")
    assert action is None
    assert category == "outfit"


def test_menu_maps_to_query_service_methods() -> None:
    queries = MagicMock()
    queries.get_players_online_summary.return_value = QueryResponse(
        query_name="get_players_online_summary",
        success=True,
        status="ok",
        data=[{"total_peak_ccu": 10}],
    )
    queries.get_most_active_island.return_value = QueryResponse(
        query_name="get_most_active_island", success=True, status="ok", data=[{}]
    )
    queries.get_top_islands.return_value = QueryResponse(
        query_name="get_top_islands", success=True, status="ok", data=[]
    )
    queries.get_shop_items_by_category.return_value = QueryResponse(
        query_name="get_shop_items_by_category",
        success=True,
        status="ok",
        data=[],
    )

    handlers = BotHandlers(queries)

    players = handlers._run_menu_action(MenuAction.PLAYERS_NOW)
    assert players.query_name == "get_players_online_summary"
    queries.get_players_online_summary.assert_called_once()

    island = handlers._run_menu_action(MenuAction.MOST_ACTIVE_ISLAND)
    assert island.query_name == "get_most_active_island"

    top = handlers._run_menu_action(MenuAction.TOP_ISLANDS)
    assert top.query_name == "get_top_islands"
    queries.get_top_islands.assert_called_with(500)

    shop = handlers._run_shop_category("outfit")
    assert shop.query_name == "get_shop_items_by_category"
    queries.get_shop_items_by_category.assert_called_with("outfit")
