"""The playground page, its API and the emulated Bot API."""

from collections.abc import AsyncIterator

import pytest
from aiogram import Bot, Dispatcher, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from app.playground.chat import PlaygroundChat
from app.playground.server import create_playground_app
from app.playground.session import UnsupportedMethodError

Client = TestClient[web.Request, web.Application]


@pytest.fixture
async def client(chat: PlaygroundChat) -> AsyncIterator[Client]:
    async with TestClient(TestServer(create_playground_app(chat, "Test Bot"))) as client:
        yield client


async def test_serves_the_page(client: Client) -> None:
    response = await client.get("/")

    assert response.status == 200
    assert "Playground" in await response.text()


async def test_chat_through_the_api(client: Client) -> None:
    response = await client.post("/api/messages", json={"text": "/add Buy milk"})
    await client.post("/api/messages", json={"text": "/notes"})
    state = await (await client.get("/api/state")).json()

    assert response.status == 200
    assert state["appName"] == "Test Bot"
    assert {"command": "/notes", "description": "Show your notes"} in state["commands"]
    senders = [message["sender"] for message in state["messages"]]
    assert senders == ["user", "bot", "user", "bot"]
    listing = state["messages"][-1]
    assert listing["html"] is True
    assert listing["buttons"][0][0]["text"] == "✕ 1"

    pressed = await client.post(
        "/api/callbacks",
        json={"messageId": listing["id"], "data": listing["buttons"][0][0]["data"]},
    )
    body = await pressed.json()
    assert body["notices"] == [{"text": "Note deleted.", "kind": "toast"}]
    assert body["messages"][-1]["edited"] is True


async def test_rejects_bad_requests(client: Client) -> None:
    empty = await client.post("/api/messages", json={"text": ""})
    broken = await client.post("/api/messages", data=b"{not json")
    missing = await client.post("/api/callbacks", json={"messageId": 99, "data": "x"})

    assert empty.status == 400
    assert broken.status == 400
    assert missing.status == 404
    assert "not in the chat" in (await missing.json())["error"]


async def test_reset_clears_the_conversation(client: Client) -> None:
    await client.post("/api/messages", json={"text": "/add"})

    state = await (await client.post("/api/reset")).json()
    await client.post("/api/messages", json={"text": "/cancel"})
    after = await (await client.get("/api/state")).json()

    assert state["messages"] == []
    assert after["messages"][-1]["text"] == "There is nothing to cancel."


def _custom_chat(router: Router) -> PlaygroundChat:
    dispatcher = Dispatcher()
    dispatcher.include_router(router)
    return PlaygroundChat(dispatcher)


async def test_reply_keyboards_are_shown_and_removed() -> None:
    router = Router()

    @router.message(Command("menu"))
    async def menu(message: Message) -> None:
        keyboard = [[KeyboardButton(text="Yes"), KeyboardButton(text="No")]]
        await message.answer("Pick one", reply_markup=ReplyKeyboardMarkup(keyboard=keyboard))

    @router.message(Command("hide"))
    async def hide(message: Message) -> None:
        await message.answer("Hidden", reply_markup=ReplyKeyboardRemove())

    chat = _custom_chat(router)
    await chat.send("/menu")
    assert chat.reply_keyboard == [["Yes", "No"]]
    await chat.send("/hide")
    assert chat.reply_keyboard is None


async def test_edits_behave_like_telegram() -> None:
    router = Router()

    @router.message(Command("same"))
    async def same(message: Message) -> None:
        sent = await message.answer("Hello")
        await sent.edit_text("Hello")

    chat = _custom_chat(router)
    with pytest.raises(TelegramBadRequest, match="message is not modified"):
        await chat.send("/same")


async def test_unsupported_methods_fail_loudly() -> None:
    router = Router()

    @router.message(Command("dice"))
    async def dice(message: Message, bot: Bot) -> None:
        await bot.send_dice(message.chat.id)

    chat = _custom_chat(router)
    with pytest.raises(UnsupportedMethodError, match="does not emulate SendDice"):
        await chat.send("/dice")
