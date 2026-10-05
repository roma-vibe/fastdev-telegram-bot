"""Inline keyboards and callback data of the notes feature."""

from collections.abc import Sequence
from enum import StrEnum

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.features.notes.models import Note


class NoteAction(StrEnum):
    DELETE = "delete"


class NoteCallback(CallbackData, prefix="note"):
    """Packed into `callback_data` (at most 64 bytes), e.g. `note:delete:42`."""

    action: NoteAction
    note_id: int


def notes_keyboard(notes: Sequence[Note]) -> InlineKeyboardMarkup | None:
    """One delete button per note, numbered like the list; None when there are no notes."""
    if not notes:
        return None
    builder = InlineKeyboardBuilder()
    for number, note in enumerate(notes, start=1):
        builder.button(
            text=f"✕ {number}",
            callback_data=NoteCallback(action=NoteAction.DELETE, note_id=note.id),
        )
    builder.adjust(5)
    return builder.as_markup()
