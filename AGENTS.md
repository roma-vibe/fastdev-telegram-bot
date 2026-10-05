# Telegram Bot skeleton — instructions for AI agents

This repository is a fastDev skeleton (`telegram-bot`). It is not a project: fastDev copies `files/` into
new projects and renders `*.tmpl` files. Read the fastDev skeleton authoring guide first
(MCP tool `get_authoring_guide`, or `docs/skeleton-authoring.md` in the fastDev repository).

- Change `template.toml` and `files/` only; `files/AGENTS.md.tmpl` and `files/SPEC.md.tmpl` are the
  instructions of the future projects, not of this repository.
- Do not commit, tag or edit `CHANGELOG.md` by hand: validate, verify and publish through fastDev
  (`validate_skeleton`, `verify_skeleton`, `publish_skeleton`). Publishing commits, creates the
  `vX.Y.Z` tag, pushes and updates the registry.
- Never move or delete a published tag.
- Everything is written in English.

## Working on this skeleton

- Build and test changes in a scratch copy of `files/` (rename `_gitignore` to `.gitignore`, copy
  `.env.example` to `.env`, set `APP_NAME`), with `uv sync` and `uv run poe check`; copy back
  without `.venv`, `__pycache__`, `.mypy_cache`, `.pytest_cache`, `.ruff_cache`, `.env` and databases.
- Dependencies: `[updates]` does not support uv yet. Update by hand in the scratch copy
  (`uv lock --upgrade` or `uv add pkg@latest`), check the changelogs of aiogram and pydantic, run
  the quality gate and ship `uv.lock`. Keep the lower bounds in `pyproject.toml` at the tested
  versions.
- Python or uv version: change `.python-version`, `requires-python`, the `python:3.x-slim` and
  `ghcr.io/astral-sh/uv:<version>` images in `files/Dockerfile.tmpl`, `stack` in `template.toml` and
  the docs together. aiogram declares the Python versions it supports (`requires-python`).
- The playground (`files/app/playground/`) emulates only the Bot API methods the example uses;
  extend `_handle_api_call` together with its tests when the example grows.
- Keep `files/AGENTS.md.tmpl`, `files/README.md.tmpl` and `files/SPEC.md.tmpl` in sync with the
  code and every Docker mode.
