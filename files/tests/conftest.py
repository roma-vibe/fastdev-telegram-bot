"""Shared fixtures: settings without `.env`, a migrated in-memory database, the bot and a chat."""

from collections.abc import AsyncIterator

import aiosqlite
import pytest
from aiogram import Dispatcher

from app.bot import create_dispatcher
from app.config import Settings
from app.db.database import IN_MEMORY, open_database
from app.db.migrator import run_migrations
from app.playground.chat import PlaygroundChat
from tests.helpers import make_settings


@pytest.fixture(autouse=True)
def _isolated_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests never see the variables of the shell or container they run in."""
    for name in Settings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)


@pytest.fixture
def settings() -> Settings:
    return make_settings()


@pytest.fixture
async def db() -> AsyncIterator[aiosqlite.Connection]:
    async with open_database(IN_MEMORY) as connection:
        await run_migrations(connection)
        yield connection


@pytest.fixture
def dispatcher(settings: Settings, db: aiosqlite.Connection) -> Dispatcher:
    return create_dispatcher(settings, db)


@pytest.fixture
def chat(dispatcher: Dispatcher, settings: Settings) -> PlaygroundChat:
    """A conversation with the real dispatcher: `await chat.send("/start")`."""
    return PlaygroundChat(dispatcher, bot_name=settings.app_name)
