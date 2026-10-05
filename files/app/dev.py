"""Development mode: the playground and, with a BOT_TOKEN, long polling; restarts on changes."""

import asyncio
import logging
import shlex
import sys
from contextlib import suppress
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramUnauthorizedError
from aiogram.utils.token import TokenValidationError

from app.bot import create_bot, create_dispatcher
from app.config import BAD_TOKEN_HINT, ENV_FILE, ROOT_DIR, Settings
from app.db.database import open_database
from app.db.migrator import run_migrations
from app.playground.chat import PlaygroundChat
from app.playground.server import create_playground_app
from app.web import serve, wait_for_stop_signal

logger = logging.getLogger(__name__)

APP_DIR = ROOT_DIR / "app"


def run_with_reload() -> None:
    """Runs `python -m app dev --no-reload` and restarts it when `app/` or `.env` change."""
    # watchfiles is a dev dependency: imported here so production never needs it.
    from watchfiles import Change, DefaultFilter, run_process

    class _Filter(DefaultFilter):
        def __call__(self, change: Change, path: str) -> bool:
            file = Path(path)
            watched = file == ENV_FILE or APP_DIR in file.parents
            return watched and super().__call__(change, path)

    def _report(changes: set[tuple[Change, str]]) -> None:
        files = sorted({str(Path(path).relative_to(ROOT_DIR)) for _, path in changes})
        logger.info("Restarting: %s changed", ", ".join(files))

    logging.getLogger("watchfiles").setLevel(logging.WARNING)  # `_report` says what changed
    command = shlex.join([sys.executable, "-m", "app", "dev", "--no-reload"])
    run_process(
        ROOT_DIR, target=command, target_type="command", watch_filter=_Filter(), callback=_report
    )


async def serve_dev(settings: Settings) -> None:
    """Serves the playground; also polls Telegram when BOT_TOKEN is set. Stops on SIGINT/SIGTERM."""
    async with open_database(settings.database_file) as db:
        await run_migrations(db)
        dispatcher = create_dispatcher(settings, db)
        chat = PlaygroundChat(dispatcher, bot_name=settings.app_name)
        app = create_playground_app(chat, settings.app_name)
        async with serve(app, settings.playground_host, settings.playground_port):
            logger.info(
                "%s playground: http://localhost:%d", settings.app_name, settings.playground_port
            )
            bot = telegram_bot(settings)
            polling = asyncio.create_task(_poll(dispatcher, bot)) if bot else None
            try:
                await wait_for_stop_signal()
            finally:
                if polling is not None:
                    polling.cancel()
                    with suppress(asyncio.CancelledError):
                        await polling


def telegram_bot(settings: Settings) -> Bot | None:
    """The bot to poll with, or None (and a log line) when BOT_TOKEN is empty or malformed."""
    token = settings.bot_token.get_secret_value().strip()
    if not token:
        logger.warning(
            "BOT_TOKEN is empty: Telegram is not connected, only the playground works. "
            "Put a token from @BotFather into .env; the bot restarts by itself."
        )
        return None
    try:
        return create_bot(token, api_url=settings.telegram_api_url)
    except TokenValidationError:
        logger.error("BOT_TOKEN is malformed: %s", BAD_TOKEN_HINT)
        return None


async def _poll(dispatcher: Dispatcher, bot: Bot) -> None:
    """Long polling that logs failures instead of stopping the playground."""
    try:
        # Polling does not work while a webhook is set: use a separate bot for development.
        await bot.delete_webhook()
        await dispatcher.start_polling(bot, handle_signals=False)
    except TelegramUnauthorizedError:
        logger.error("Telegram rejected BOT_TOKEN: %s", BAD_TOKEN_HINT)
    except Exception:
        logger.exception("Long polling stopped; the playground keeps running")
    finally:
        await bot.session.close()
