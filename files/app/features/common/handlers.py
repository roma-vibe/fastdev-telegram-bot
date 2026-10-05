"""/start, /help, /cancel, the fallback for everything else, and the error replies."""

import logging

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import BotCommand, ErrorEvent, Message

from app.config import Settings
from app.features.common import texts

logger = logging.getLogger(__name__)

COMMANDS = [
    BotCommand(command="start", description="Start the bot"),
    BotCommand(command="help", description="What the bot can do"),
    BotCommand(command="cancel", description="Cancel the current action"),
]


def create_router() -> Router:
    """Include it first: /cancel must win over the state handlers of other features."""
    router = Router(name="common")
    router.message.register(start, CommandStart())
    router.message.register(show_help, Command("help"))
    router.message.register(cancel, Command("cancel"))
    return router


def create_fallback_router() -> Router:
    """Include it last: it answers every message that no other handler took."""
    router = Router(name="fallback")
    router.message.register(unknown_message)
    return router


async def start(message: Message, state: FSMContext, settings: Settings) -> None:
    await state.clear()
    first_name = message.from_user.first_name if message.from_user else "there"
    await message.answer(texts.welcome(first_name, settings.app_name))


async def show_help(message: Message) -> None:
    await message.answer(texts.HELP)


async def cancel(message: Message, state: FSMContext) -> None:
    if await state.get_state() is None:
        await message.answer(texts.NOTHING_TO_CANCEL)
        return
    await state.clear()
    await message.answer(texts.CANCELLED)


async def unknown_message(message: Message) -> None:
    await message.answer(texts.UNKNOWN)


async def reply_with_error(event: ErrorEvent) -> None:
    """For `AppError`: the message of the error is meant for the user."""
    await _reply(event, str(event.exception))


async def reply_with_failure(event: ErrorEvent) -> None:
    """For any other exception: log it with the traceback and apologise."""
    logger.error("Update %s failed", event.update.update_id, exc_info=event.exception)
    await _reply(event, texts.FAILED)


async def _reply(event: ErrorEvent, text: str) -> None:
    update = event.update
    if update.callback_query is not None:
        await update.callback_query.answer(text, show_alert=True)
    elif update.message is not None:
        await update.message.answer(text, parse_mode=None)
