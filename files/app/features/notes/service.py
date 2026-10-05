"""Business rules of the notes feature. No Telegram objects and no SQL here."""

from app.errors import NotFoundError, ValidationError
from app.features.notes.models import Note
from app.features.notes.repository import NotesRepository

MAX_NOTE_LENGTH = 500
MAX_NOTES_PER_USER = 20


class NotesService:
    def __init__(self, repository: NotesRepository) -> None:
        self._repository = repository

    async def add(self, user_id: int, text: str) -> Note:
        text = text.strip()
        if not text:
            msg = "A note needs some text."
            raise ValidationError(msg)
        if len(text) > MAX_NOTE_LENGTH:
            msg = f"A note can be at most {MAX_NOTE_LENGTH} characters long."
            raise ValidationError(msg)
        if await self._repository.count_for_user(user_id) >= MAX_NOTES_PER_USER:
            msg = f"You can keep up to {MAX_NOTES_PER_USER} notes. Delete one first."
            raise ValidationError(msg)
        return await self._repository.add(user_id, text)

    async def list_notes(self, user_id: int) -> list[Note]:
        return await self._repository.list_for_user(user_id)

    async def delete(self, user_id: int, note_id: int) -> None:
        if not await self._repository.delete(user_id, note_id):
            msg = "This note does not exist anymore."
            raise NotFoundError(msg)
