"""Telegram handlers of the notes feature: parse the update, call the service, reply."""

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import BotCommand, CallbackQuery, Message

from app.features.notes import keyboards, texts
from app.features.notes.keyboards import NoteAction, NoteCallback
from app.features.notes.service import NotesService
from app.features.notes.states import NoteForm

COMMANDS = [
    BotCommand(command="add", description="Add a note"),
    BotCommand(command="notes", description="Show your notes"),
]


def create_router() -> Router:
    """A new router per dispatcher (a router can belong to one parent only)."""
    router = Router(name="notes")
    router.message.register(add_note, Command("add"))
    router.message.register(list_notes, Command("notes"))
    # Text after a bare /add; commands are left to their own handlers.
    router.message.register(receive_note_text, NoteForm.text, F.text, ~F.text.startswith("/"))
    router.callback_query.register(delete_note, NoteCallback.filter(F.action == NoteAction.DELETE))
    return router


async def add_note(
    message: Message, command: CommandObject, state: FSMContext, notes: NotesService
) -> None:
    if message.from_user is None:
        return
    if not command.args:
        await state.set_state(NoteForm.text)
        await message.answer(texts.ASK_TEXT)
        return
    note = await notes.add(message.from_user.id, command.args)
    await message.answer(texts.saved(note))


async def receive_note_text(message: Message, state: FSMContext, notes: NotesService) -> None:
    if message.from_user is None or message.text is None:
        return
    note = await notes.add(message.from_user.id, message.text)
    await state.clear()
    await message.answer(texts.saved(note))


async def list_notes(message: Message, notes: NotesService) -> None:
    if message.from_user is None:
        return
    items = await notes.list_notes(message.from_user.id)
    await message.answer(texts.notes_list(items), reply_markup=keyboards.notes_keyboard(items))


async def delete_note(
    callback: CallbackQuery, callback_data: NoteCallback, notes: NotesService
) -> None:
    await notes.delete(callback.from_user.id, callback_data.note_id)
    items = await notes.list_notes(callback.from_user.id)
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            texts.notes_list(items), reply_markup=keyboards.notes_keyboard(items)
        )
    await callback.answer(texts.DELETED)
