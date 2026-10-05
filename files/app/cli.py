"""`python -m app [run|dev|migrate]` — the bot's command line (wrapped by `uv run poe …`)."""

import argparse
import asyncio
import sys
from collections.abc import Sequence

from aiogram.exceptions import TelegramUnauthorizedError
from aiogram.utils.token import TokenValidationError

from app.config import BAD_TOKEN_HINT, ConfigError, load_settings
from app.dev import run_with_reload, serve_dev
from app.logs import setup_logging
from app.runner import migrate, run_bot


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python -m app", description="Run the bot, the dev playground or migrations."
    )
    commands = parser.add_subparsers(dest="command", metavar="command")
    commands.add_parser("run", help="run the bot: polling or webhook (BOT_MODE); the default")
    dev = commands.add_parser("dev", help="playground + polling, restarting on file changes")
    dev.add_argument("--no-reload", action="store_true", help="do not watch files")
    commands.add_parser("migrate", help="apply pending database migrations")
    args = parser.parse_args(argv)

    if args.command == "dev" and not args.no_reload:
        setup_logging("INFO")
        run_with_reload()
        return
    try:
        settings = load_settings()
        setup_logging(settings.log_level)
        match args.command:
            case "dev":
                asyncio.run(serve_dev(settings))
            case "migrate":
                asyncio.run(migrate(settings))
            case _:
                asyncio.run(run_bot(settings))
    except ConfigError as error:
        sys.exit(f"error: {error}")
    except TokenValidationError:
        sys.exit(f"error: BOT_TOKEN is malformed: {BAD_TOKEN_HINT}")
    except TelegramUnauthorizedError:
        sys.exit(f"error: Telegram rejected BOT_TOKEN: {BAD_TOKEN_HINT}")
