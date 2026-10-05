"""Messages of the notes feature. The bot uses HTML parse mode: quote every user-provided value."""

from collections.abc import Sequence

from aiogram import html

from app.features.notes.models import Note

PREVIEW_LENGTH = 120

ASK_TEXT = "Send the text of the note, or /cancel."
DELETED = "Note deleted."


def saved(note: Note) -> str:
    return f"Saved: {html.quote(note.text)}"


def notes_list(notes: Sequence[Note]) -> str:
    if not notes:
        return "You have no notes yet. Add one with /add followed by the text."
    lines = [html.bold(f"Your notes ({len(notes)})")]
    lines += [
        f"{number}. {html.quote(_preview(note.text))}" for number, note in enumerate(notes, 1)
    ]
    lines += ["", "Tap a number below to delete that note."]
    return "\n".join(lines)


def _preview(text: str) -> str:
    text = " ".join(text.split())
    return text if len(text) <= PREVIEW_LENGTH else text[: PREVIEW_LENGTH - 1] + "…"
