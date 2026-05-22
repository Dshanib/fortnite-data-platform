"""Menu callback routing tests."""

from __future__ import annotations

from unittest.mock import MagicMock

from bot.handlers import BotHandlers
from bot.intents import MenuAction, menu_action_for_callback
from common.models import QueryResponse


def test_menu_callback_constants() -> None:
    assert menu_action_for_callback("menu:current_activity") == MenuAction.CURRENT_ACTIVITY
    assert menu_action_for_callback("menu:top_islands") == MenuAction.TOP_ISLANDS
    assert menu_action_for_callback("invalid") is None


def test_menu_maps_to_query_service_methods() -> None:
    queries = MagicMock()
    queries.get_current_ccu.return_value = QueryResponse(
        query_name="get_current_ccu", success=True, status="ok", data=[{}]
    )
    queries.get_top_islands.return_value = QueryResponse(
        query_name="get_top_islands", success=True, status="ok", data=[]
    )
    queries.get_shop_rarity_distribution.return_value = QueryResponse(
        query_name="get_shop_rarity_distribution",
        success=False,
        status="no_data",
        data=[],
        message="empty",
    )

    handlers = BotHandlers(queries)

    ccu = handlers._run_menu_action(MenuAction.CURRENT_ACTIVITY)
    assert ccu.query_name == "get_current_ccu"
    queries.get_current_ccu.assert_called_once()

    top = handlers._run_menu_action(MenuAction.TOP_ISLANDS)
    assert top.query_name == "get_top_islands"
    queries.get_top_islands.assert_called_with(10)

    shop = handlers._run_menu_action(MenuAction.SHOP_SUMMARY)
    assert shop.status == "no_data"
