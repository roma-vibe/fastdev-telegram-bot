# Telegram Bot

Telegram bot in Python on aiogram 3 with SQLite, long polling in development and polling or a webhook in production. It ships a notes example that goes through handlers, services, repositories and SQL migrations, a browser playground to chat with the bot locally without a token, pytest tests, Ruff and strict mypy. Choose it for chat, helper and notification bots that keep their own data; Docker can run everything, so only Docker or uv is needed on the Mac.

This repository is a [fastDev](https://github.com/roma-vibe/fastDev) project skeleton (`telegram-bot`). fastDev lists it
from a registry, downloads it when first used and creates named, ready-to-run projects from it.

- `template.toml` — the manifest: requirements, options, env, setup steps and commands.
- `files/` — the files of a new project (`*.tmpl` files are rendered with the project name and options).
- `CHANGELOG.md` — what changed in every version.

Versions are the `vX.Y.Z` tags of this repository and never change once published.

## Stack

| Part | Choice |
| --- | --- |
| Runtime | Python 3.14, managed by uv 0.12 (`.python-version`, `uv.lock`); uv ≥ 0.9 reads the lockfile |
| Bot framework | aiogram 3.31 (asyncio): routers, filters, FSM, `CallbackData`, HTML parse mode |
| HTTP | aiohttp 3.14 (bundled with aiogram): `/health`, webhook endpoint, playground |
| Database | SQLite through aiosqlite 0.22, plain SQL migrations, no ORM |
| Configuration | pydantic-settings 2.15 reading `.env` literally (no `${VAR}` expansion) into typed `Settings` |
| Tasks | Poe the Poet 0.48 (`uv run poe <task>`) |
| Quality | Ruff 0.16 (lint + format), mypy 2.3 strict with the pydantic plugin, pytest 9.1 + pytest-asyncio 1.4, warnings are errors |
| Dev reload | watchfiles 1.3 (restarts on changes to `app/` and `.env`) |
| Docker | `python:3.14-slim` multi-stage image with uv from `ghcr.io/astral-sh/uv:0.12.21`, non-root user |

## Options

| Choice | Options (default first) | What changes |
| --- | --- | --- |
| `docker` | **`full`** — everything in Docker · `run` — develop with uv, Docker for the production container · `none` — no Docker files | Docker files, setup steps and commands. `full` is the default because Python 3.14/uv are usually not installed on the Mac. |
| `data` (Docker only) | **`volume`** — named volume · `local` — the project's `data/` folder | `DOCKER_DATA` in `.env` |
| `mode` | **`polling`** — long polling · `webhook` — HTTPS webhook | `BOT_MODE` in `.env` and the docs; both modes are always in the code |

## What a new project gets

- A runnable bot: `/start` greets with `APP_NAME` from `.env`, `/help`, `/cancel`, a fallback reply, user-facing error replies and logged failures.
- The **notes** example through every layer: SQL migration → repository → service (rules and limits) → handlers with a command, a two-step FSM conversation, inline delete buttons with `CallbackData` → texts with safe HTML quoting.
- A **playground**: `dev` serves a chat page (`PLAYGROUND_PORT`) that feeds updates into the real dispatcher and emulates the Bot API, so the bot can be tried without a token or Internet; tests use the same `PlaygroundChat`.
- Production entry point with long polling or webhook (secret token, allowed updates from the handlers), `/health`, graceful shutdown on SIGTERM, optional self-hosted Bot API server (`TELEGRAM_API_URL`).
- 49 tests (config, migrations, service, conversations, webhook, stop signals, playground, dev mode), `uv run poe check` green with zero warnings.
- `AGENTS.md` (architecture rules, how to add features, commands, conventions, Telegram specifics), `SPEC.md` for the bot's specification, `README.md` for people.
- Free ports (`APP_PORT`, `PLAYGROUND_PORT`), a generated `WEBHOOK_SECRET`, the project name in `.env` and `pyproject.toml`.

## Commands in a project

| Key | Host (`none`, `run`) | `full` |
| --- | --- | --- |
| `dev` (primary) | `uv run poe dev` | `docker compose up dev` |
| `start` | `uv run poe start` | `docker compose up --build app` |
| `test` / `check` / `lint` / `format` / `db-migrate` | `uv run poe test` / `check` / `lint` / `fix` / `migrate` | the same in `docker compose run --rm dev …` |
| `docker-up` / `docker-down` / `docker-logs` | `run` only | `docker-down`, `docker-logs` |

Setup: `uv sync --locked` (host) or `docker compose run --rm dev uv sync --locked` + `docker compose build app` (`full`). fastDev writes the project's slug into `pyproject.toml` and `uv.lock`, so the locked install passes.

## Preview

`[preview]` runs `dev`: the playground opens at `http://localhost:${PLAYGROUND_PORT}`, where the owner can chat with the bot (`/start`, `/add Buy milk`, `/notes`, the ✕ buttons) without a token. With the default choices the preview runs inside Docker.

## Verification

`[verify]` runs `check` and `docker-build` (Docker modes only) for the defaults (`full`, `volume`, `polling`) and for `full` + `local` + `webhook`, `run` + `webhook` and `none`. Host variants need uv on the login PATH.
