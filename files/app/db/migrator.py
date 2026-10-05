"""Applies `migrations/NNN_name.sql` files in order and records them in `schema_migrations`."""

import logging
import re
from dataclasses import dataclass
from pathlib import Path

import aiosqlite

MIGRATIONS_DIR = Path(__file__).parent / "migrations"
_FILE_NAME = re.compile(r"^(?P<version>\d{3})_[a-z0-9_]+\.sql$")

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Migration:
    version: int
    name: str
    path: Path


def find_migrations(directory: Path = MIGRATIONS_DIR) -> list[Migration]:
    """Migration files sorted by version; rejects bad names and duplicate numbers."""
    migrations: dict[int, Migration] = {}
    for path in sorted(directory.glob("*.sql")):
        match = _FILE_NAME.match(path.name)
        if match is None:
            msg = f"Bad migration file name {path.name!r}: use NNN_snake_case.sql"
            raise ValueError(msg)
        version = int(match["version"])
        if version in migrations:
            msg = f"Duplicate migration number {version:03d}: {path.name}"
            raise ValueError(msg)
        migrations[version] = Migration(version, path.name, path)
    return [migrations[version] for version in sorted(migrations)]


async def run_migrations(db: aiosqlite.Connection, directory: Path = MIGRATIONS_DIR) -> list[str]:
    """Applies pending migrations, each in its own transaction. Returns the applied file names."""
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
        ) STRICT
        """
    )
    applied = {row[0] for row in await db.execute_fetchall("SELECT version FROM schema_migrations")}
    done: list[str] = []
    for migration in find_migrations(directory):
        if migration.version in applied:
            continue
        sql = migration.path.read_text(encoding="utf-8")
        # The file name was validated above, so it is safe inside the script.
        script = (
            f"BEGIN;\n{sql}\n;\n"
            f"INSERT INTO schema_migrations (version, name) "
            f"VALUES ({migration.version}, '{migration.name}');\nCOMMIT;"
        )
        try:
            await db.executescript(script)
        except Exception:
            if db.in_transaction:
                await db.rollback()
            raise
        logger.info("Applied migration %s", migration.name)
        done.append(migration.name)
    return done
