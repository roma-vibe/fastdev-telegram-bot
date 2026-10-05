import sqlite3
from pathlib import Path

import aiosqlite
import pytest

from app.db.database import IN_MEMORY, open_database
from app.db.migrator import find_migrations, run_migrations


async def test_applies_every_migration_once() -> None:
    async with open_database(IN_MEMORY) as db:
        first = await run_migrations(db)
        second = await run_migrations(db)
        rows = await db.execute_fetchall("SELECT version, name FROM schema_migrations")

    assert first == [migration.name for migration in find_migrations()]
    assert second == []
    assert [tuple(row) for row in rows] == [(m.version, m.name) for m in find_migrations()]


async def test_failed_migration_is_rolled_back(tmp_path: Path) -> None:
    (tmp_path / "001_create_things.sql").write_text("CREATE TABLE things (id INTEGER);")
    (tmp_path / "002_broken.sql").write_text(
        "CREATE TABLE other (id INTEGER);\nINSERT INTO missing VALUES (1);"
    )

    async with open_database(IN_MEMORY) as db:
        with pytest.raises(sqlite3.OperationalError, match="no such table: missing"):
            await run_migrations(db, tmp_path)
        tables = {row[0] for row in await db.execute_fetchall("SELECT name FROM sqlite_master")}
        versions = await db.execute_fetchall("SELECT version FROM schema_migrations")

    assert "things" in tables
    assert "other" not in tables
    assert [row[0] for row in versions] == [1]


@pytest.mark.parametrize(
    ("files", "message"),
    [
        (["1_short.sql"], "Bad migration file name"),
        (["001_Upper.sql"], "Bad migration file name"),
        (["001_one.sql", "001_two.sql"], "Duplicate migration number 001"),
    ],
)
def test_rejects_bad_file_names(tmp_path: Path, files: list[str], message: str) -> None:
    for name in files:
        (tmp_path / name).write_text("SELECT 1;")

    with pytest.raises(ValueError, match=message):
        find_migrations(tmp_path)


async def test_database_file_is_created_with_wal(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "bot.sqlite"

    async with open_database(path) as db:
        async with db.execute("PRAGMA journal_mode") as cursor:
            row = await cursor.fetchone()
        assert isinstance(db, aiosqlite.Connection)

    assert path.exists()
    assert row is not None
    assert row[0] == "wal"
