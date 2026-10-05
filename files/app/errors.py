"""Errors raised by services. Their message is shown to the user as is (see `features/common`)."""


class AppError(Exception):
    """An expected problem the user can fix; `str(error)` is a user-facing sentence."""


class ValidationError(AppError):
    """The input breaks a business rule (empty text, too long, limit reached…)."""


class NotFoundError(AppError):
    """The requested item does not exist (or belongs to another user)."""
