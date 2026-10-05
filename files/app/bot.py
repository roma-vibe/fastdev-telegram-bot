"""Composition root: the Bot client and the Dispatcher with every feature wired in."""

import aiosqlite
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.session.base import BaseSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.enums import ParseMode
from aiogram.filters import ExceptionTypeFilter
from aiogram.fsm.storage.base import BaseStorage
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from app.config import Settings
from app.errors import AppError
from app.features.common import handlers as common
from app.features.notes import handlers as notes
from app.features.notes.repository import NotesRepository
from app.features.notes.service import NotesService

BOT_COMMANDS: list[BotCommand] = [*common.COMMANDS, *notes.COMMANDS]
"""The command menu Telegram shows next to the message field (set on startup)."""


def create_bot(token: str, *, api_url: str = "", session: BaseSession | None = None) -> Bot:
    """A Bot API client. Replies use HTML parse mode unless a call says otherwise.

    `api_url` points to a self-hosted Bot API server (TELEGRAM_API_URL); empty means Telegram's.
    """
    if session is None and api_url:
        session = AiohttpSession(api=TelegramAPIServer.from_base(api_url))
    return Bot(
        token=token,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher(
    settings: Settings, db: aiosqlite.Connection, storage: BaseStorage | None = None
) -> Dispatcher:
    """Builds services and routers. Handlers receive workflow data by parameter name."""
    dispatcher = Dispatcher(
        storage=storage or MemoryStorage(),
        settings=settings,
        notes=NotesService(NotesRepository(db)),
    )
    dispatcher.include_routers(
        common.create_router(),
        notes.create_router(),
        common.create_fallback_router(),
    )
    dispatcher.errors.register(common.reply_with_error, ExceptionTypeFilter(AppError))
    dispatcher.errors.register(common.reply_with_failure)
    dispatcher.startup.register(set_bot_commands)
    return dispatcher


async def set_bot_commands(bot: Bot) -> None:
    await bot.set_my_commands(BOT_COMMANDS)
