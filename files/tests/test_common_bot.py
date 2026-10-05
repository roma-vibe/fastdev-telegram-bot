"""/start, /help, /cancel, the fallback reply and error handling."""

import logging

import pytest

from app.bot import BOT_COMMANDS, set_bot_commands
from app.features.notes.service import NotesService
from app.playground.chat import PlaygroundChat


async def test_start_greets_with_the_app_name(chat: PlaygroundChat) -> None:
    await chat.send("/start")

    text = chat.last_bot_message.plain_text
    assert text.startswith("Hi, Alex! This is Test Bot.")
    assert "/add Buy milk" in text


async def test_help_lists_the_commands(chat: PlaygroundChat) -> None:
    await chat.send("/help")

    # Guards /help against drifting from the command menu when features are added.
    text = chat.last_bot_message.plain_text
    for command in BOT_COMMANDS:
        assert f"/{command.command} " in text


async def test_cancel_without_anything_to_cancel(chat: PlaygroundChat) -> None:
    await chat.send("/cancel")

    assert chat.last_bot_message.text == "There is nothing to cancel."


async def test_unknown_messages_get_a_hint(chat: PlaygroundChat) -> None:
    await chat.send("/unknown")
    assert "Send /help" in chat.last_bot_message.text

    await chat.send("hello")
    assert "Send /help" in chat.last_bot_message.text


async def test_unexpected_errors_are_logged_and_apologised_for(
    chat: PlaygroundChat, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    async def broken(*_args: object) -> None:
        msg = "database is on fire"
        raise RuntimeError(msg)

    monkeypatch.setattr(NotesService, "list_notes", broken)

    with caplog.at_level(logging.ERROR):
        await chat.send("/notes")

    assert chat.last_bot_message.text == "Something went wrong on my side. Please try again later."
    assert "database is on fire" in caplog.text


async def test_command_menu_is_set_on_startup(chat: PlaygroundChat) -> None:
    await set_bot_commands(chat.bot)  # the playground accepts it like Telegram would
