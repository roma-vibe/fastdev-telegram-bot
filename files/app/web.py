"""The bot's HTTP server on APP_PORT: `GET /health` and, in webhook mode, the webhook endpoint."""

import asyncio
import signal
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from app.config import Settings

SETTINGS_KEY = web.AppKey("settings", Settings)


def create_web_app(
    settings: Settings,
    *,
    dispatcher: Dispatcher | None = None,
    bot: Bot | None = None,
    webhook_secret: str | None = None,
) -> web.Application:
    """Health check always; the webhook route when a dispatcher and a bot are given."""
    app = web.Application()
    app[SETTINGS_KEY] = settings
    app.router.add_get("/health", health)
    if dispatcher is not None and bot is not None:
        SimpleRequestHandler(dispatcher, bot, secret_token=webhook_secret).register(
            app, path=settings.webhook_path
        )
        # Runs the dispatcher's startup/shutdown handlers with the server.
        setup_application(app, dispatcher, bot=bot)
    return app


async def health(request: web.Request) -> web.Response:
    settings = request.app[SETTINGS_KEY]
    return web.json_response({"status": "ok", "app": settings.app_name, "mode": settings.bot_mode})


@asynccontextmanager
async def serve(app: web.Application, host: str, port: int) -> AsyncIterator[None]:
    """Serves `app` on host:port until the block exits."""
    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    try:
        await web.TCPSite(runner, host, port).start()
        yield
    finally:
        await runner.cleanup()


async def wait_for_stop_signal() -> None:
    """Returns on SIGINT (Ctrl+C) or SIGTERM (`docker stop`, fastDev Stop).

    The handlers stay until the event loop closes: a stop often arrives as several signals
    (fastDev signals the whole process group, uv and Poe forward them again), and the repeated
    ones must not interrupt the shutdown.
    """
    loop = asyncio.get_running_loop()
    stop = asyncio.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)
    await stop.wait()
