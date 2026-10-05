from pathlib import Path

import pytest

from app.config import ROOT_DIR, ConfigError, Settings, load_settings
from tests.helpers import make_settings


def test_defaults_and_derived_values() -> None:
    settings = make_settings(webhook_base_url="https://bot.example.com/")

    assert settings.bot_mode == "polling"
    assert settings.database_file == ROOT_DIR / "data" / "app.sqlite"
    assert settings.webhook_url == "https://bot.example.com/telegram/webhook"


def test_reads_env_file_and_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        'APP_NAME="From File"\nAPP_SLUG=from-file\nBOT_MODE=Webhook\nLOG_LEVEL=debug\n'
        "DB_PATH=/tmp/bot.sqlite\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("APP_SLUG", "from-env")

    settings = load_settings(env_file)

    assert settings.app_name == "From File"
    assert settings.app_slug == "from-env"  # the environment wins over .env
    assert settings.bot_mode == "webhook"
    assert settings.log_level == "DEBUG"
    assert settings.database_file == Path("/tmp/bot.sqlite")


def test_env_file_values_are_not_expanded(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("APP_NAME='My \"Shop\" $HOME ${HOME}'\nAPP_SLUG=shop\n", encoding="utf-8")

    assert load_settings(env_file).app_name == 'My "Shop" $HOME ${HOME}'


def test_invalid_configuration_is_one_readable_error(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("APP_SLUG=bot\nAPP_PORT=nope\n", encoding="utf-8")

    with pytest.raises(ConfigError) as error:
        load_settings(tmp_path / ".env")

    assert "APP_NAME: Field required" in str(error.value)
    assert "APP_PORT:" in str(error.value)


def test_webhook_path_must_be_absolute() -> None:
    with pytest.raises(ValueError, match="must start with /"):
        make_settings(webhook_path="webhook")


def test_require_bot_token() -> None:
    with pytest.raises(ConfigError, match="BOT_TOKEN is empty"):
        make_settings().require_bot_token()
    assert make_settings(bot_token=" 123:abc ").require_bot_token() == "123:abc"


def test_require_webhook() -> None:
    with pytest.raises(ConfigError, match="WEBHOOK_BASE_URL"):
        make_settings(webhook_base_url="http://insecure.example.com").require_webhook()
    with pytest.raises(ConfigError, match="WEBHOOK_SECRET"):
        make_settings(webhook_base_url="https://bot.example.com").require_webhook()

    settings: Settings = make_settings(
        webhook_base_url="https://bot.example.com", webhook_secret="s3cret"
    )
    assert settings.require_webhook() == ("https://bot.example.com/telegram/webhook", "s3cret")
