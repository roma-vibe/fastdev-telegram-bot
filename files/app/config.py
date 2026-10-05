"""Settings from `.env` and the environment. The only module that reads configuration."""

from collections.abc import Mapping
from pathlib import Path
from typing import Literal

from dotenv import dotenv_values
from pydantic import Field, SecretStr, ValidationError, field_validator
from pydantic_settings import (
    BaseSettings,
    DotEnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

ROOT_DIR = Path(__file__).resolve().parent.parent
"""Project root: `.env` and relative paths such as `DB_PATH` are resolved against it."""

ENV_FILE = ROOT_DIR / ".env"

BAD_TOKEN_HINT = "copy the token from @BotFather into .env (it looks like 123456789:AAE…)."

BotMode = Literal["polling", "webhook"]
LogLevel = Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]


class ConfigError(Exception):
    """The configuration is missing or invalid; the message tells the owner what to fix."""


class LiteralDotEnvSource(DotEnvSettingsSource):
    """Reads `.env` without `${VAR}` expansion, so values reach the app exactly as written.

    python-dotenv expands `${VAR}` even in single quotes; Docker Compose does not.
    """

    def _read_env_file(self, file_path: Path) -> Mapping[str, str | None]:
        values = dotenv_values(file_path, encoding=self.env_file_encoding, interpolate=False)
        return {key.lower(): value for key, value in values.items()}


class Settings(BaseSettings):
    """Typed settings. Environment variables override `.env`; field `app_name` reads `APP_NAME`."""

    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(min_length=1)
    app_slug: str = Field(min_length=1)

    bot_token: SecretStr = SecretStr("")
    bot_mode: BotMode = "polling"
    telegram_api_url: str = ""
    """Empty: api.telegram.org. Set it to use a self-hosted Bot API server."""

    app_host: str = "localhost"
    app_port: int = Field(default=8080, ge=1, le=65535)

    webhook_base_url: str = ""
    webhook_path: str = "/telegram/webhook"
    webhook_secret: SecretStr = SecretStr("")

    playground_host: str = "localhost"
    playground_port: int = Field(default=8090, ge=1, le=65535)

    db_path: Path = Path("data/app.sqlite")
    log_level: LogLevel = "INFO"

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """The default order (environment variables win over `.env`), `.env` read literally."""
        if isinstance(dotenv_settings, DotEnvSettingsSource):
            dotenv_settings = LiteralDotEnvSource(settings_cls, env_file=dotenv_settings.env_file)
        return init_settings, env_settings, dotenv_settings, file_secret_settings

    @field_validator("bot_mode", mode="before")
    @classmethod
    def _lowercase(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("log_level", mode="before")
    @classmethod
    def _uppercase(cls, value: object) -> object:
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator("webhook_path")
    @classmethod
    def _check_webhook_path(cls, value: str) -> str:
        if not value.startswith("/"):
            msg = "must start with /"
            raise ValueError(msg)
        return value

    @property
    def database_file(self) -> Path:
        """`DB_PATH` as an absolute path."""
        return self.db_path if self.db_path.is_absolute() else ROOT_DIR / self.db_path

    @property
    def webhook_url(self) -> str:
        """Public URL that Telegram posts updates to."""
        return self.webhook_base_url.rstrip("/") + self.webhook_path

    def require_bot_token(self) -> str:
        """The bot token, or a `ConfigError` explaining how to get one."""
        token = self.bot_token.get_secret_value().strip()
        if not token:
            msg = (
                "BOT_TOKEN is empty. Create a bot with @BotFather in Telegram and put its token "
                "into .env (BOT_TOKEN=...). The playground (`uv run poe dev`) works without one."
            )
            raise ConfigError(msg)
        return token

    def require_webhook(self) -> tuple[str, str]:
        """Webhook URL and secret for `BOT_MODE=webhook`, or a `ConfigError`."""
        if not self.webhook_base_url.startswith("https://"):
            msg = (
                "BOT_MODE=webhook needs WEBHOOK_BASE_URL: the public https:// address that "
                "forwards to APP_PORT (for example https://bot.example.com)."
            )
            raise ConfigError(msg)
        secret = self.webhook_secret.get_secret_value()
        if not secret:
            msg = (
                "BOT_MODE=webhook needs WEBHOOK_SECRET (1-256 characters: A-Z, a-z, 0-9, _ and -)."
            )
            raise ConfigError(msg)
        return self.webhook_url, secret


def load_settings(env_file: Path | None = ENV_FILE) -> Settings:
    """Reads the settings, turning validation errors into one readable `ConfigError`."""
    try:
        return Settings(_env_file=env_file)
    except ValidationError as error:
        problems = "\n".join(
            f"  {'.'.join(str(part) for part in item['loc']).upper()}: {item['msg']}"
            for item in error.errors()
        )
        msg = f"Invalid configuration in .env or the environment:\n{problems}"
        raise ConfigError(msg) from error
