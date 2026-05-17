"""Telegram message handlers (query_service only)."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from bot.formatters import format_query_response, help_text
from bot.intents import Intent, detect_intent
from common.logging import get_logger
from serving.query_service import QueryService

logger = get_logger(__name__)


class BotHandlers:
    """Route intents to predefined query_service methods."""

    def __init__(self, query_service: QueryService) -> None:
        self._queries = query_service

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start."""
        if update.message:
            await update.message.reply_text(help_text())

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help."""
        if update.message:
            await update.message.reply_text(help_text())

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle free-text messages via intent routing."""
        if not update.message or not update.message.text:
            return

        intent = detect_intent(update.message.text)
        logger.info("Detected intent=%s", intent.value)

        response = self._dispatch(intent)
        if update.message:
            await update.message.reply_text(format_query_response(response))

    def _dispatch(self, intent: Intent):
        """Map intent to query_service call."""
        mapping = {
            Intent.CURRENT_CCU: self._queries.get_current_ccu,
            Intent.AVG_CCU_TODAY: self._queries.get_avg_today,
            Intent.ANOMALY_CHECK: self._queries.get_recent_anomalies,
            Intent.SHOP_SUMMARY: self._queries.get_shop_rarity_distribution,
            Intent.SOURCE_HEALTH: self._queries.get_source_health,
        }
        if intent == Intent.HELP:
            from common.models import QueryResponse

            return QueryResponse(
                query_name="help",
                success=True,
                data=[{"hint": help_text()}],
                message="OK",
            )
        if intent == Intent.UNKNOWN:
            from common.models import QueryResponse

            return QueryResponse(
                query_name="unknown",
                success=False,
                message="Unknown command. Send 'help' for options.",
            )
        handler = mapping.get(intent)
        if handler is None:
            from common.models import QueryResponse

            return QueryResponse(query_name=intent.value, success=False, message="Unsupported")
        return handler()
