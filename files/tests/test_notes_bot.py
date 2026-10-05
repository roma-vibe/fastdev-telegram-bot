"""The notes feature as the user sees it: conversations through the real dispatcher."""

import pytest

from app.features.notes.service import MAX_NOTE_LENGTH
from app.playground.chat import ChatMessage, Notice, PlaygroundChat


def _first_button_data(message: ChatMessage) -> str:
    assert message.reply_markup is not None
    data = message.reply_markup.inline_keyboard[0][0].callback_data
    assert data is not None
    return data


async def test_add_with_text(chat: PlaygroundChat) -> None:
    await chat.send("/add Buy milk")

    assert chat.last_bot_message.text == "Saved: Buy milk"


async def test_add_asks_for_text_and_cancel_stops_it(chat: PlaygroundChat) -> None:
    await chat.send("/add")
    assert chat.last_bot_message.text == "Send the text of the note, or /cancel."

    await chat.send("/cancel")
    assert chat.last_bot_message.text == "Cancelled."

    await chat.send("Not a note")
    assert "did not understand" in chat.last_bot_message.text


async def test_add_in_two_steps(chat: PlaygroundChat) -> None:
    await chat.send("/add")
    await chat.send("/notes")  # commands still work while the bot waits for the text
    assert "no notes yet" in chat.last_bot_message.text

    await chat.send("Call mom")
    assert chat.last_bot_message.text == "Saved: Call mom"


async def test_validation_errors_are_replied(chat: PlaygroundChat) -> None:
    await chat.send("/add " + "x" * (MAX_NOTE_LENGTH + 1))

    assert chat.last_bot_message.text == f"A note can be at most {MAX_NOTE_LENGTH} characters long."


async def test_user_text_is_escaped(chat: PlaygroundChat) -> None:
    await chat.send("/add <b>not bold</b> & more")

    message = chat.last_bot_message
    assert message.html
    assert message.text == "Saved: &lt;b&gt;not bold&lt;/b&gt; &amp; more"
    assert message.plain_text == "Saved: <b>not bold</b> & more"


async def test_list_and_delete(chat: PlaygroundChat) -> None:
    await chat.send("/add Buy milk")
    await chat.send("/add Call mom")
    await chat.send("/notes")

    listing = chat.last_bot_message
    assert listing.plain_text.splitlines()[:3] == ["Your notes (2)", "1. Call mom", "2. Buy milk"]
    assert listing.reply_markup is not None
    buttons = listing.reply_markup.inline_keyboard[0]
    assert [button.text for button in buttons] == ["✕ 1", "✕ 2"]

    delete_first = buttons[0].callback_data
    assert delete_first is not None
    notices = await chat.press(listing.id, delete_first)

    assert notices == [Notice("Note deleted.", "toast")]
    assert listing.edited
    assert listing.plain_text.splitlines()[:2] == ["Your notes (1)", "1. Buy milk"]


async def test_stale_buttons_show_an_alert(chat: PlaygroundChat) -> None:
    await chat.send("/add Buy milk")
    await chat.send("/notes")
    old_listing = chat.last_bot_message
    await chat.send("/notes")
    await chat.press(chat.last_bot_message.id, _first_button_data(chat.last_bot_message))

    notices = await chat.press(old_listing.id, _first_button_data(old_listing))

    assert notices == [Notice("This note does not exist anymore.", "alert")]


async def test_deleting_the_last_note_removes_the_keyboard(chat: PlaygroundChat) -> None:
    await chat.send("/add Only one")
    await chat.send("/notes")
    listing = chat.last_bot_message

    await chat.press(listing.id, _first_button_data(listing))

    assert listing.reply_markup is None
    assert "no notes yet" in listing.text


async def test_unknown_button_is_rejected(chat: PlaygroundChat) -> None:
    await chat.send("/start")

    with pytest.raises(LookupError, match="has no button"):
        await chat.press(chat.last_bot_message.id, "note:delete:1")
