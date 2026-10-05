"""Domain types of the notes feature."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Note:
    id: int
    user_id: int
    """Telegram user id of the owner."""
    text: str
    created_at: datetime
