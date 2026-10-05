"""All SQL of the notes feature."""

from datetime import datetime

import aiosqlite

from app.features.notes.models import Note

_COLUMNS = "id, user_id, text, created_at"


def _to_note(row: aiosqlite.Row) -> Note:
    return Note(
        id=row["id"],
        user_id=row["user_id"],
        text=row["text"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )


class NotesRepository:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self._db = db

    async def add(self, user_id: int, text: str) -> Note:
        async with self._db.execute(
            f"INSERT INTO notes (user_id, text) VALUES (?, ?) RETURNING {_COLUMNS}",
            (user_id, text),
        ) as cursor:
            row = await cursor.fetchone()
        if row is None:  # pragma: no cover - RETURNING always yields the row
            msg = "INSERT … RETURNING returned no row"
            raise RuntimeError(msg)
        return _to_note(row)

    async def list_for_user(self, user_id: int) -> list[Note]:
        """Notes of a user, newest first."""
        rows = await self._db.execute_fetchall(
            f"SELECT {_COLUMNS} FROM notes WHERE user_id = ? ORDER BY id DESC",
            (user_id,),
        )
        return [_to_note(row) for row in rows]

    async def count_for_user(self, user_id: int) -> int:
        async with self._db.execute(
            "SELECT count(*) FROM notes WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
        return int(row[0]) if row else 0

    async def delete(self, user_id: int, note_id: int) -> bool:
        """Deletes a note of this user; False when there was none."""
        async with self._db.execute(
            "DELETE FROM notes WHERE id = ? AND user_id = ?", (note_id, user_id)
        ) as cursor:
            return cursor.rowcount > 0
