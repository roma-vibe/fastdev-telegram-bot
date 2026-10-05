"""A private chat between a local user and the bot, driven without Telegram.

`PlaygroundChat` turns text and button presses into Telegram updates, feeds them to the real
dispatcher (same routers, services and database as in production) and records what the bot sends
back. The playground page (`server.py`) and the tests use it.
"""

import asyncio
import html
import itertools
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from aiogram import Bot, Dispatcher
from aiogram.client.default import Default
from aiogram.enums import ChatType, ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.methods import (
    AnswerCallbackQuery,
    DeleteMessage,
    DeleteMyCommands,
    DeleteWebhook,
    EditMessageReplyMarkup,
    EditMessageText,
    GetMe,
    SendChatAction,
    SendMessage,
    SetMyCommands,
    TelegramMethod,
)
from aiogram.types import (
    CallbackQuery,
    Chat,
    InlineKeyboardMarkup,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
    User,
)

from app.bot import create_bot
from app.playground.session import PlaygroundSession, UnsupportedMethodError

PLAYGROUND_TOKEN = "1000000001:playground"
"""Looks like a real token so aiogram accepts it; never sent anywhere."""

PLAYGROUND_USER = User(
    id=1000000002, is_bot=False, first_name="Alex", username="playground_user", language_code="en"
)

_TAG = re.compile(r"<[^>]+>")


@dataclass(slots=True)
class ChatMessage:
    id: int
    sender: Literal["user", "bot"]
    text: str
    html: bool = False
    """The text uses Telegram's HTML markup (the bot's default parse mode)."""
    reply_markup: InlineKeyboardMarkup | None = None
    chat_id: int | str | None = None
    """Set when the bot sent the message to another chat than the playground chat."""
    edited: bool = False

    @property
    def plain_text(self) -> str:
        """The text without HTML tags, as the user reads it."""
        return html.unescape(_TAG.sub("", self.text)) if self.html else self.text


@dataclass(frozen=True, slots=True)
class Notice:
    """A pop-up: an answered callback query, or an error of the playground itself."""

    text: str
    kind: Literal["toast", "alert", "error"]


class PlaygroundChat:
    def __init__(
        self, dispatcher: Dispatcher, *, bot_name: str = "Bot", user: User = PLAYGROUND_USER
    ) -> None:
        self.dispatcher = dispatcher
        self.user = user
        self.bot = create_bot(PLAYGROUND_TOKEN, session=PlaygroundSession(self._handle_api_call))
        self.bot_user = User(id=self.bot.id, is_bot=True, first_name=bot_name, username="bot")
        self.chat = Chat(
            id=user.id, type=ChatType.PRIVATE, first_name=user.first_name, username=user.username
        )
        self.messages: list[ChatMessage] = []
        self.reply_keyboard: list[list[str]] | None = None
        """Buttons of the last reply keyboard; pressing one sends its text."""
        self._notices: list[Notice] = []
        self._message_ids = itertools.count(1)
        self._update_ids = itertools.count(1)
        self._lock = asyncio.Lock()

    @property
    def bot_messages(self) -> list[ChatMessage]:
        return [message for message in self.messages if message.sender == "bot"]

    @property
    def last_bot_message(self) -> ChatMessage:
        if not self.bot_messages:
            msg = "The bot has not sent anything yet"
            raise LookupError(msg)
        return self.bot_messages[-1]

    async def send(self, text: str) -> list[Notice]:
        """The user sends a text message. Returns the pop-ups the bot showed while handling it."""
        async with self._lock:
            message = ChatMessage(id=next(self._message_ids), sender="user", text=text)
            self.messages.append(message)
            update = Update(
                update_id=next(self._update_ids),
                message=Message(
                    message_id=message.id,
                    date=datetime.now(UTC),
                    chat=self.chat,
                    from_user=self.user,
                    text=text,
                ),
            )
            return await self._feed(update)

    async def press(self, message_id: int, callback_data: str) -> list[Notice]:
        """The user taps an inline button of a bot message."""
        async with self._lock:
            message = self._find(message_id)
            buttons = message.reply_markup.inline_keyboard if message.reply_markup else []
            if not any(button.callback_data == callback_data for row in buttons for button in row):
                msg = f"Message {message_id} has no button with this callback data"
                raise LookupError(msg)
            update = Update(
                update_id=next(self._update_ids),
                callback_query=CallbackQuery(
                    id=str(next(self._update_ids)),
                    from_user=self.user,
                    chat_instance=str(self.chat.id),
                    message=self._to_telegram(message),
                    data=callback_data,
                ),
            )
            return await self._feed(update)

    async def reset(self) -> None:
        """Clears the conversation and the user's FSM state (data in the database stays)."""
        async with self._lock:
            self.messages.clear()
            self.reply_keyboard = None
            key = StorageKey(bot_id=self.bot.id, chat_id=self.chat.id, user_id=self.user.id)
            await FSMContext(storage=self.dispatcher.storage, key=key).clear()

    async def _feed(self, update: Update) -> list[Notice]:
        self._notices = []
        await self.dispatcher.feed_update(self.bot, update)
        notices, self._notices = self._notices, []
        return notices

    def _find(self, message_id: int | None) -> ChatMessage:
        for message in self.messages:
            if message.id == message_id:
                return message
        msg = f"Message {message_id} is not in the chat"
        raise LookupError(msg)

    def _to_telegram(self, message: ChatMessage) -> Message:
        return Message(
            message_id=message.id,
            date=datetime.now(UTC),
            chat=self.chat,
            from_user=self.bot_user if message.sender == "bot" else self.user,
            text=message.plain_text,
            reply_markup=message.reply_markup,
        ).as_(self.bot)

    # --- The Bot API as seen by the bot ------------------------------------------------------

    def _handle_api_call(self, bot: Bot, method: TelegramMethod[Any]) -> object:
        match method:
            case SendMessage():
                return self._send_message(bot, method)
            case EditMessageText():
                return self._edit_message(bot, method, method.message_id, method.text or "")
            case EditMessageReplyMarkup():
                message = self._find(method.message_id)
                return self._edit_message(bot, method, method.message_id, message.text)
            case DeleteMessage():
                self.messages.remove(self._find(method.message_id))
                return True
            case AnswerCallbackQuery():
                if method.text:
                    self._notices.append(
                        Notice(method.text, "alert" if method.show_alert else "toast")
                    )
                return True
            case GetMe():
                return self.bot_user
            case SendChatAction() | SetMyCommands() | DeleteMyCommands() | DeleteWebhook():
                return True
            case _:
                name = type(method).__name__
                text = (
                    f"The playground does not emulate {name} yet; add it to app/playground/chat.py."
                )
                self._notices.append(Notice(text, "error"))
                raise UnsupportedMethodError(text)

    def _send_message(self, bot: Bot, method: SendMessage) -> Message:
        markup = method.reply_markup
        if isinstance(markup, ReplyKeyboardMarkup):
            self.reply_keyboard = [[button.text for button in row] for row in markup.keyboard]
        elif isinstance(markup, ReplyKeyboardRemove):
            self.reply_keyboard = None
        message = ChatMessage(
            id=next(self._message_ids),
            sender="bot",
            text=method.text,
            html=_parse_mode(bot, method.parse_mode) == ParseMode.HTML,
            reply_markup=markup if isinstance(markup, InlineKeyboardMarkup) else None,
            chat_id=None if method.chat_id == self.chat.id else method.chat_id,
        )
        self.messages.append(message)
        return self._to_telegram(message)

    def _edit_message(
        self,
        bot: Bot,
        method: EditMessageText | EditMessageReplyMarkup,
        message_id: int | None,
        text: str,
    ) -> Message:
        message = self._find(message_id)
        is_html = (
            _parse_mode(bot, method.parse_mode) == ParseMode.HTML
            if isinstance(method, EditMessageText)
            else message.html
        )
        if (text, is_html, method.reply_markup) == (
            message.text,
            message.html,
            message.reply_markup,
        ):
            # Telegram rejects edits that change nothing; so does the playground.
            raise TelegramBadRequest(method=method, message="Bad Request: message is not modified")
        message.text, message.html, message.reply_markup = text, is_html, method.reply_markup
        message.edited = True
        return self._to_telegram(message)


def _parse_mode(bot: Bot, value: str | Default | None) -> str | None:
    """Resolves `Default("parse_mode")` placeholders to the bot's default."""
    if isinstance(value, Default):
        resolved = bot.default[value.name]
        return resolved if isinstance(resolved, str) else None
    return value
