"""Opens the SQLite database used by every repository."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite

IN_MEMORY = ":memory:"


@asynccontextmanager
async def open_database(path: Path | str) -> AsyncIterator[aiosqlite.Connection]:
    """Opens `path` (or `":memory:"` in tests) in autocommit mode with foreign keys and WAL on.

    Every statement commits on its own; group statements with `BEGIN` … `COMMIT` when they must
    succeed together (see `migrator.py`).
    """
    if isinstance(path, Path):
        path.parent.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(path, isolation_level=None)
    try:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON")
        await db.execute("PRAGMA busy_timeout = 5000")
        if str(path) != IN_MEMORY:
            await db.execute("PRAGMA journal_mode = WAL")
        yield db
    finally:
        await db.close()
