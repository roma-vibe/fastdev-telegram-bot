"""Production entry points: run the bot (polling or webhook) and apply migrations."""

import logging

from aiogram import Bot, Dispatcher

from app.bot import create_bot, create_dispatcher
from app.config import Settings
from app.db.database import open_database
from app.db.migrator import run_migrations
from app.web import create_web_app, serve, wait_for_stop_signal

logger = logging.getLogger(__name__)


async def migrate(settings: Settings) -> None:
    async with open_database(settings.database_file) as db:
        applied = await run_migrations(db)
    logger.info("Migrations applied: %s", ", ".join(applied) if applied else "none (up to date)")


async def run_bot(settings: Settings) -> None:
    """Runs until SIGINT/SIGTERM. Raises `ConfigError` when BOT_TOKEN or webhook settings miss."""
    token = settings.require_bot_token()
    webhook = settings.require_webhook() if settings.bot_mode == "webhook" else None
    async with (
        open_database(settings.database_file) as db,
        create_bot(token, api_url=settings.telegram_api_url) as bot,
    ):
        await run_migrations(db)
        dispatcher = create_dispatcher(settings, db)
        if webhook is None:
            await _run_polling(settings, bot, dispatcher)
        else:
            url, secret = webhook
            await _run_webhook(settings, bot, dispatcher, url, secret)


async def _run_polling(settings: Settings, bot: Bot, dispatcher: Dispatcher) -> None:
    async with serve(create_web_app(settings), settings.app_host, settings.app_port):
        logger.info(
            "%s: long polling; health on http://%s:%d/health",
            settings.app_name,
            settings.app_host,
            settings.app_port,
        )
        # Telegram does not deliver updates by polling while a webhook is set.
        await bot.delete_webhook()
        # Stops on SIGINT/SIGTERM and closes the bot session.
        await dispatcher.start_polling(bot)


async def _run_webhook(
    settings: Settings, bot: Bot, dispatcher: Dispatcher, url: str, secret: str
) -> None:
    async def register_webhook(bot: Bot) -> None:
        await bot.set_webhook(
            url,
            secret_token=secret,
            allowed_updates=dispatcher.resolve_used_update_types(),
        )

    dispatcher.startup.register(register_webhook)
    app = create_web_app(settings, dispatcher=dispatcher, bot=bot, webhook_secret=secret)
    async with serve(app, settings.app_host, settings.app_port):
        logger.info(
            "%s: webhook %s → http://%s:%d%s",
            settings.app_name,
            url,
            settings.app_host,
            settings.app_port,
            settings.webhook_path,
        )
        await wait_for_stop_signal()
