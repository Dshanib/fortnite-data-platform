"""Telegram handlers — Hebrew menu-first UX via QueryService."""

from __future__ import annotations

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from bot import copy_he as t
from bot.formatters import (
    back_menu_keyboard,
    format_menu_response,
    help_text,
    main_menu_keyboard,
    unknown_input_text,
    welcome_text,
)
from bot.intents import Intent, MenuAction, detect_intent, menu_action_for_callback
from common.logging import get_logger
from common.models import QueryResponse
from serving.query_service import QueryService

logger = get_logger(__name__)

_PARSE = ParseMode.HTML


class BotHandlers:
    """Route menu callbacks and optional free-text to QueryService."""

    def __init__(self, query_service: QueryService) -> None:
        self._queries = query_service

    async def _send_message(
        self,
        update: Update,
        text: str,
        *,
        keyboard=None,
        edit: bool = False,
    ) -> None:
        markup = keyboard or main_menu_keyboard()
        if edit and update.callback_query and update.callback_query.message:
            await update.callback_query.message.edit_text(
                text,
                parse_mode=_PARSE,
                reply_markup=markup,
                disable_web_page_preview=True,
            )
            return
        if update.message:
            await update.message.reply_text(
                text,
                parse_mode=_PARSE,
                reply_markup=markup,
                disable_web_page_preview=True,
            )
        elif update.callback_query and update.callback_query.message:
            await update.callback_query.message.reply_text(
                text,
                parse_mode=_PARSE,
                reply_markup=markup,
                disable_web_page_preview=True,
            )

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start — welcome + main menu."""
        await self._send_message(update, welcome_text())

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help — show guide with back to menu."""
        await self._send_message(
            update, help_text(), keyboard=back_menu_keyboard()
        )

    async def menu_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /menu — main menu."""
        await self._send_message(update, welcome_text())

    async def handle_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle inline menu button presses."""
        query = update.callback_query
        if not query:
            return

        action = menu_action_for_callback(query.data or "")
        if action is None:
            await query.answer(t.UNKNOWN_ACTION, show_alert=True)
            return

        if action == MenuAction.HOME:
            await query.answer()
            await self._send_message(update, welcome_text(), edit=True)
            return

        if action == MenuAction.HELP:
            await query.answer()
            await self._send_message(
                update, help_text(), keyboard=back_menu_keyboard(), edit=True
            )
            return

        await query.answer(t.LOADING)
        response = self._run_menu_action(action)
        text = format_menu_response(response)
        await self._send_message(
            update, text, keyboard=back_menu_keyboard(), edit=True
        )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle free-text as secondary fallback."""
        if not update.message or not update.message.text:
            return

        intent = detect_intent(update.message.text)
        logger.info("Detected intent=%s", intent.value)

        if intent in (Intent.HELP, Intent.UNKNOWN):
            if intent == Intent.UNKNOWN:
                await self._send_message(update, unknown_input_text())
            else:
                await self._send_message(update, welcome_text())
            return

        response = self._dispatch_intent(intent)
        await self._send_message(
            update,
            format_menu_response(response),
            keyboard=back_menu_keyboard(),
        )

    def _query_method_for_menu(self, action: MenuAction):
        mapping = {
            MenuAction.CURRENT_ACTIVITY: self._queries.get_current_ccu,
            MenuAction.TOP_ISLANDS: lambda: self._queries.get_top_islands(10),
            MenuAction.SHOP_SUMMARY: self._queries.get_shop_rarity_distribution,
            MenuAction.SOURCE_HEALTH: self._queries.get_source_health,
            MenuAction.ANOMALIES: self._queries.get_recent_anomalies,
        }
        return mapping.get(action)

    def _run_menu_action(self, action: MenuAction) -> QueryResponse:
        try:
            handler = self._query_method_for_menu(action)
            if handler is None:
                return QueryResponse(
                    query_name=action.value,
                    success=False,
                    status="error",
                    data=[],
                    message=t.UNKNOWN_ACTION,
                )
            return handler()
        except Exception as exc:
            logger.exception("Menu action %s failed", action.value)
            return QueryResponse(
                query_name=action.value,
                success=False,
                status="error",
                data=[],
                message=str(exc),
            )

    def _dispatch_intent(self, intent: Intent) -> QueryResponse:
        mapping = {
            Intent.CURRENT_CCU: self._queries.get_current_ccu,
            Intent.AVG_CCU_TODAY: self._queries.get_avg_today,
            Intent.ANOMALY_CHECK: self._queries.get_recent_anomalies,
            Intent.SHOP_SUMMARY: self._queries.get_shop_rarity_distribution,
            Intent.SOURCE_HEALTH: self._queries.get_source_health,
            Intent.TOP_ISLANDS: lambda: self._queries.get_top_islands(10),
        }
        handler = mapping.get(intent)
        if handler is None:
            return QueryResponse(
                query_name=intent.value,
                success=False,
                status="error",
                data=[],
                message=t.UNKNOWN_ACTION,
            )
        try:
            return handler()
        except Exception as exc:
            logger.exception("Intent %s failed", intent.value)
            return QueryResponse(
                query_name=intent.value,
                success=False,
                status="error",
                data=[],
                message=str(exc),
            )
