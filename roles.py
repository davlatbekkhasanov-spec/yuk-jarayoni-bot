"""Huquqlar: admin (Railway) va mas'ul (bot ichida)."""

from __future__ import annotations

from config import is_admin
from db import is_operator


def can_manage_yuk(user_id: int | None) -> bool:
    """Yuk keldi / yakunlash."""
    if user_id is None:
        return False
    uid = int(user_id)
    return is_admin(uid) or is_operator(uid)
