"""Telegram bot application entrypoint."""

from __future__ import annotations

import sys

from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from bot.formatters import format_error, main_menu_keyboard
from bot.handlers import BotHandlers
from bot.single_instance import ensure_single_instance
from common.logging import configure_logging, get_logger
from common.models import QueryResponse
from config.settings import get_settings
from serving.query_service import QueryService

logger = get_logger(__name__)


def _configure_stdio_utf8() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def build_application() -> Application:
    """Build python-telegram-bot application with Hebrew menu handlers."""
    settings = get_settings()
    configure_logging(settings.log_level)

    query_service = QueryService(settings)
    handlers = BotHandlers(query_service)

    app = Application.builder().token(settings.telegram_bot_token).build()
    app.add_handler(CommandHandler("start", handlers.start))
    app.add_handler(CommandHandler("help", handlers.help_command))
    app.add_handler(CommandHandler("menu", handlers.menu_command))
    app.add_handler(CallbackQueryHandler(handlers.handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_message))
    app.add_error_handler(_error_handler)
    return app


async def _error_handler(update: object, context) -> None:
    """Log and show a friendly Hebrew error without crashing the bot."""
    logger.exception("Telegram handler error: %s", context.error)
    if not update or not getattr(update, "effective_chat", None):
        return
    chat = update.effective_chat
    if chat is None:
        return
    response = QueryResponse(
        query_name="error",
        success=False,
        status="error",
        data=[],
        message=str(context.error) if context.error else "unknown",
    )
    await context.bot.send_message(
        chat_id=chat.id,
        text=format_error(response),
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(),
    )


def main() -> None:
    """Run the Telegram bot."""
    _configure_stdio_utf8()
    ensure_single_instance()
    logger.info("Starting Fortnite Telegram bot (Hebrew UI)")
    app = build_application()
    app.run_polling()


if __name__ == "__main__":
    main()
