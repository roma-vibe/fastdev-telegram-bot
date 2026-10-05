import logging

import pytest

from app.dev import telegram_bot
from tests.helpers import make_settings


def test_polls_only_with_a_token(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        assert telegram_bot(make_settings()) is None
    assert "BOT_TOKEN is empty" in caplog.text


def test_a_malformed_token_keeps_the_playground_running(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.ERROR):
        assert telegram_bot(make_settings(bot_token="not-a-token")) is None
    assert "BOT_TOKEN is malformed" in caplog.text


def test_creates_the_bot_for_polling() -> None:
    bot = telegram_bot(make_settings(bot_token="123456:abc"))

    assert bot is not None
    assert bot.id == 123456
