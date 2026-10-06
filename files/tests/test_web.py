"""The bot's HTTP server: health check, webhook endpoint and stop signals."""

import asyncio
import os
import signal

from aiogram import Dispatcher
from aiohttp.test_utils import TestClient, TestServer

from app.playground.chat import PlaygroundChat
from app.web import create_web_app, wait_for_stop_signal
from tests.helpers import make_settings

SECRET_HEADER = "X-Telegram-Bot-Api-Secret-Token"


async def test_health_reports_the_app_name() -> None:
    app = create_web_app(make_settings(bot_mode="webhook"))

    async with TestClient(TestServer(app)) as client:
        response = await client.get("/health")
        body = await response.json()

    assert response.status == 200
    assert body == {"status": "ok", "app": "Test Bot", "mode": "webhook"}


async def test_webhook_feeds_updates_to_the_dispatcher(
    dispatcher: Dispatcher, chat: PlaygroundChat
) -> None:
    settings = make_settings(bot_mode="webhook")
    # The playground bot stands in for Telegram: replies are recorded in `chat`.
    app = create_web_app(settings, dispatcher=dispatcher, bot=chat.bot, webhook_secret="s3cret")
    update = {
        "update_id": 1,
        "message": {
            "message_id": 1,
            "date": 1_700_000_000,
            "chat": {"id": chat.user.id, "type": "private"},
            "from": {"id": chat.user.id, "is_bot": False, "first_name": "Alex"},
            "text": "/help",
        },
    }

    async with TestClient(TestServer(app)) as client:
        rejected = await client.post(
            settings.webhook_path, json=update, headers={SECRET_HEADER: "wrong"}
        )
        accepted = await client.post(
            settings.webhook_path, json=update, headers={SECRET_HEADER: "s3cret"}
        )
        # Updates are handled in the background after Telegram gets its 200.
        for _ in range(100):
            if chat.bot_messages:
                break
            await asyncio.sleep(0.01)

    assert rejected.status == 401
    assert accepted.status == 200
    assert "What I can do" in chat.last_bot_message.text


async def test_repeated_stop_signals_do_not_interrupt_the_shutdown() -> None:
    waiting = asyncio.create_task(wait_for_stop_signal())
    await asyncio.sleep(0)  # the task installs its signal handlers

    os.kill(os.getpid(), signal.SIGTERM)
    await asyncio.wait_for(waiting, timeout=1)
    # fastDev, uv and Poe may each send a signal: the later ones must be absorbed, not raise
    # KeyboardInterrupt in the middle of the shutdown.
    os.kill(os.getpid(), signal.SIGINT)
    await asyncio.sleep(0.05)
