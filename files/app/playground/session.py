"""An aiogram session that answers Bot API calls locally instead of sending them to Telegram."""

from collections.abc import AsyncGenerator, Callable
from typing import Any, cast

from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.methods import TelegramMethod
from aiogram.methods.base import TelegramType

ApiHandler = Callable[[Bot, TelegramMethod[Any]], object]


class UnsupportedMethodError(Exception):
    """The bot called a Bot API method that the playground does not emulate."""


class PlaygroundSession(BaseSession):
    """Passes every Bot API call to `handler`, which returns what Telegram would return."""

    def __init__(self, handler: ApiHandler) -> None:
        super().__init__()
        self._handler = handler

    # The signatures below are fixed by aiogram's BaseSession, hence the `timeout` parameters.
    async def make_request(
        self,
        bot: Bot,
        method: TelegramMethod[TelegramType],
        timeout: int | None = None,  # noqa: ASYNC109
    ) -> TelegramType:
        return cast(TelegramType, self._handler(bot, method))

    async def stream_content(
        self,
        url: str,
        headers: dict[str, Any] | None = None,
        timeout: int = 30,  # noqa: ASYNC109
        chunk_size: int = 65536,
        raise_for_status: bool = True,
    ) -> AsyncGenerator[bytes]:
        msg = "The playground cannot download files."
        raise UnsupportedMethodError(msg)
        yield b""  # type: ignore[unreachable]  # makes this method an async generator

    async def close(self) -> None:
        return None
