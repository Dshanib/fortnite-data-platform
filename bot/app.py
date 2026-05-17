"""Telegram bot application entrypoint."""

from __future__ import annotations

from telegram.ext import Application, CommandHandler, MessageHandler, filters

from bot.handlers import BotHandlers
from common.logging import configure_logging, get_logger
from config.settings import get_settings
from serving.query_service import QueryService

logger = get_logger(__name__)


def build_application() -> Application:
    """Build python-telegram-bot application with handlers."""
    settings = get_settings()
    configure_logging(settings.log_level)

    query_service = QueryService(settings)
    handlers = BotHandlers(query_service)

    app = Application.builder().token(settings.telegram_bot_token).build()
    app.add_handler(CommandHandler("start", handlers.start))
    app.add_handler(CommandHandler("help", handlers.help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_message))
    return app


def main() -> None:
    """Run the Telegram bot."""
    logger.info("Starting Fortnite Telegram bot")
    app = build_application()
    app.run_polling()


if __name__ == "__main__":
    main()
