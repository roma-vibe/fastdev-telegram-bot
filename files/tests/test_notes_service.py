import aiosqlite
import pytest

from app.errors import NotFoundError, ValidationError
from app.features.notes.repository import NotesRepository
from app.features.notes.service import MAX_NOTE_LENGTH, MAX_NOTES_PER_USER, NotesService

ALICE = 1
BOB = 2


@pytest.fixture
def notes(db: aiosqlite.Connection) -> NotesService:
    return NotesService(NotesRepository(db))


async def test_add_trims_and_lists_newest_first(notes: NotesService) -> None:
    first = await notes.add(ALICE, "  Buy milk ")
    second = await notes.add(ALICE, "Call mom")

    assert first.text == "Buy milk"
    assert first.user_id == ALICE
    assert first.created_at.tzinfo is not None
    assert await notes.list_notes(ALICE) == [second, first]


async def test_users_see_only_their_notes(notes: NotesService) -> None:
    note = await notes.add(ALICE, "Secret")

    assert await notes.list_notes(BOB) == []
    with pytest.raises(NotFoundError):
        await notes.delete(BOB, note.id)
    assert await notes.list_notes(ALICE) == [note]


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("   ", "A note needs some text."),
        ("x" * (MAX_NOTE_LENGTH + 1), f"at most {MAX_NOTE_LENGTH} characters"),
    ],
)
async def test_rejects_invalid_text(notes: NotesService, text: str, message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        await notes.add(ALICE, text)


async def test_limits_notes_per_user(notes: NotesService) -> None:
    for number in range(MAX_NOTES_PER_USER):
        await notes.add(ALICE, f"Note {number}")

    with pytest.raises(ValidationError, match=f"up to {MAX_NOTES_PER_USER} notes"):
        await notes.add(ALICE, "One too many")
    assert (await notes.add(BOB, "Bob is fine")).user_id == BOB


async def test_delete(notes: NotesService) -> None:
    note = await notes.add(ALICE, "Temporary")

    await notes.delete(ALICE, note.id)

    assert await notes.list_notes(ALICE) == []
    with pytest.raises(NotFoundError, match="does not exist anymore"):
        await notes.delete(ALICE, note.id)
