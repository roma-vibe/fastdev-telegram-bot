"""Messages of the common feature (HTML parse mode: quote user-provided values)."""

from aiogram import html

HELP = "\n".join(
    [
        html.bold("What I can do"),
        "/start — start over",
        "/add — add a note (send the text right after the command, or on its own)",
        "/notes — show your notes and delete them",
        "/cancel — cancel the current action",
        "/help — show this message",
    ]
)

NOTHING_TO_CANCEL = "There is nothing to cancel."
CANCELLED = "Cancelled."
UNKNOWN = "Sorry, I did not understand that. Send /help to see what I can do."
FAILED = "Something went wrong on my side. Please try again later."


def welcome(first_name: str, app_name: str) -> str:
    return (
        f"Hi, {html.quote(first_name)}! This is {html.bold(html.quote(app_name))}.\n\n"
        "I keep short notes for you. Try /add Buy milk, then /notes.\n"
        "Send /help to see every command."
    )
