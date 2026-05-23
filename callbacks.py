"""CallbackData — xavfsiz callback."""

from aiogram.filters.callback_data import CallbackData


class JoinCb(CallbackData, prefix="jn"):
    session_id: int
    closed: int = 0


class FinishCb(CallbackData, prefix="fn"):
    session_id: int
    confirm: int = 0
