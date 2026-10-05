"""Conversation states (FSM) of the notes feature."""

from aiogram.fsm.state import State, StatesGroup


class NoteForm(StatesGroup):
    text = State()
    """Waiting for the text of a new note after a bare /add."""
