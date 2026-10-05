"""The playground web page and its JSON API (development only, served by `python -m app dev`).

GET  /                → the chat page (static/index.html)
GET  /api/state       → the conversation
POST /api/messages    {"text": "..."}                 → the user sends a message
POST /api/callbacks   {"messageId": 1, "data": "..."} → the user taps an inline button
POST /api/reset       → clear the conversation and the user's FSM state
"""

from pathlib import Path
from typing import Any

from aiohttp import web
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.bot import BOT_COMMANDS
from app.playground.chat import ChatMessage, Notice, PlaygroundChat

STATIC_DIR = Path(__file__).parent / "static"
CHAT_KEY = web.AppKey("chat", PlaygroundChat)
APP_NAME_KEY = web.AppKey("app_name", str)


class SendBody(BaseModel):
    text: str = Field(min_length=1, max_length=4096)


class PressBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    message_id: int = Field(alias="messageId")
    data: str = Field(min_length=1, max_length=64)


def create_playground_app(chat: PlaygroundChat, app_name: str) -> web.Application:
    app = web.Application()
    app[CHAT_KEY] = chat
    app[APP_NAME_KEY] = app_name
    app.router.add_get("/", index)
    app.router.add_get("/api/state", get_state)
    app.router.add_post("/api/messages", post_message)
    app.router.add_post("/api/callbacks", post_callback)
    app.router.add_post("/api/reset", post_reset)
    return app


async def index(_request: web.Request) -> web.FileResponse:
    return web.FileResponse(STATIC_DIR / "index.html")


async def get_state(request: web.Request) -> web.Response:
    return _state(request, [])


async def post_message(request: web.Request) -> web.Response:
    body = await _parse(request, SendBody)
    notices = await request.app[CHAT_KEY].send(body.text)
    return _state(request, notices)


async def post_callback(request: web.Request) -> web.Response:
    body = await _parse(request, PressBody)
    try:
        notices = await request.app[CHAT_KEY].press(body.message_id, body.data)
    except LookupError as error:
        raise _error(web.HTTPNotFound, str(error)) from error
    return _state(request, notices)


async def post_reset(request: web.Request) -> web.Response:
    await request.app[CHAT_KEY].reset()
    return _state(request, [])


async def _parse[T: BaseModel](request: web.Request, model: type[T]) -> T:
    try:
        return model.model_validate_json(await request.read())
    except ValidationError as error:
        details = "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in error.errors())
        raise _error(web.HTTPBadRequest, details or "Invalid JSON body") from error


def _error(kind: type[web.HTTPError], message: str) -> web.HTTPError:
    return kind(text=web.json_response({"error": message}).text, content_type="application/json")


def _state(request: web.Request, notices: list[Notice]) -> web.Response:
    chat = request.app[CHAT_KEY]
    return web.json_response(
        {
            "appName": request.app[APP_NAME_KEY],
            "userName": chat.user.full_name,
            "commands": [
                {"command": f"/{c.command}", "description": c.description} for c in BOT_COMMANDS
            ],
            "messages": [_message(message) for message in chat.messages],
            "replyKeyboard": chat.reply_keyboard,
            "notices": [{"text": notice.text, "kind": notice.kind} for notice in notices],
        }
    )


def _message(message: ChatMessage) -> dict[str, Any]:
    rows = message.reply_markup.inline_keyboard if message.reply_markup else []
    return {
        "id": message.id,
        "sender": message.sender,
        "text": message.text,
        "html": message.html,
        "edited": message.edited,
        "chatId": message.chat_id,
        "buttons": [
            [
                {"text": button.text, "data": button.callback_data, "url": button.url}
                for button in row
            ]
            for row in rows
        ],
    }
