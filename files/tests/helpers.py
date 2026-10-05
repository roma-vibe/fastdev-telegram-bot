"""Helpers shared by tests."""

from typing import Any

from app.config import Settings


def make_settings(**overrides: Any) -> Settings:
    """Settings for tests: required values filled in, never read from `.env`."""
    values: dict[str, Any] = {"app_name": "Test Bot", "app_slug": "test-bot", **overrides}
    return Settings(_env_file=None, **values)
