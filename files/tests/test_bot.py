from aiogram.enums import ParseMode

from app.bot import create_bot


def test_bot_defaults_to_html_and_telegram_servers() -> None:
    bot = create_bot("123:abc")

    assert bot.default.parse_mode == ParseMode.HTML
    assert (
        bot.session.api.api_url("123:abc", "getMe") == "https://api.telegram.org/bot123:abc/getMe"
    )


def test_bot_can_use_a_self_hosted_api_server() -> None:
    bot = create_bot("123:abc", api_url="http://localhost:8081")

    assert bot.session.api.api_url("123:abc", "getMe") == "http://localhost:8081/bot123:abc/getMe"
