# Changelog

## 1.0.0 — 2026-10-05

- Initial version: Telegram bot on aiogram 3.31 and Python 3.14 (uv 0.12, locked in uv.lock) with SQLite through aiosqlite 0.22 and pydantic-settings 2.15 for .env configuration.
- Notes example through every layer: SQL migration, repository, service with limits, handlers for /add (inline text or a two-step FSM conversation) and /notes, inline delete buttons with CallbackData, HTML-safe texts.
- Common commands: /start greets with APP_NAME from .env, /help, /cancel and a fallback reply; AppError messages are shown to users, other failures are logged with tracebacks.
- Production run (`uv run poe start`): long polling or a webhook with a secret token (BOT_MODE), GET /health on APP_PORT, graceful shutdown on SIGTERM, optional self-hosted Bot API server (TELEGRAM_API_URL).
- Playground: `dev` serves a local chat page on PLAYGROUND_PORT that runs the real dispatcher against an emulated Bot API, so the bot can be tried without a token; tests drive the same PlaygroundChat.
- Dev mode restarts on changes to app/ and .env and long-polls Telegram when BOT_TOKEN is set; a missing, malformed or rejected token only disables polling.
- Quality gate `uv run poe check`: Ruff lint and format check, mypy strict, pytest 9 with 47 tests; warnings fail the run.
- Docker modes: none, Docker to run the app, or everything in Docker (default): dev container with reload and the playground, .venv in a volume, production image on python:3.14-slim as a non-root user with a health check.
- Data storage for containers: Docker volume (default) or the project data/ folder (DOCKER_DATA).
- Update delivery for production: long polling (default) or webhook (BOT_MODE); development always polls.
- The project slug is written into pyproject.toml and uv.lock, so setup installs with `uv sync --locked`; in Everything in Docker setup also builds the production image.
- Docker build command in both Docker modes; verification builds the production image.
- Cleanup removes the containers, volumes and local images that verifications and previews create in both Docker modes.
- .env is read by pydantic-settings (python-dotenv) and Docker Compose, so names with spaces, quotes and Cyrillic work.
- Russian translations of all manifest texts.
- Preview runs the playground (inside Docker with the default choices).
- Verified: check and docker-build for full/volume/polling, full/local/webhook, run/webhook and none (host modes with uv 0.12.21); a project named Test "Shop" Магазин on the host and in the dev container; previews in the default and No Docker modes; earlier manual runs of the production containers in run and full modes, polling and webhook against a local fake Bot API. Not tested against the real Telegram API with a real bot token.
- Settings read .env without python-dotenv's ${VAR} expansion, like Docker Compose, so a project name containing ${…} reaches the bot unchanged; a new test covers it (48 tests).
