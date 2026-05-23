"""Muhit o‘zgaruvchilari."""

from __future__ import annotations

import os
from functools import lru_cache


def _parse_ids(raw: str) -> frozenset[int]:
    out: set[int] = set()
    for part in (raw or "").replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.add(int(part))
        except ValueError:
            continue
    return frozenset(out)


@lru_cache(maxsize=1)
def settings():
    token = (os.getenv("BOT_TOKEN") or "").strip()
    group_raw = (os.getenv("GROUP_ID") or "").strip()
    group_id = int(group_raw) if group_raw.lstrip("-").isdigit() else None
    admin_ids = _parse_ids(os.getenv("ADMIN_IDS") or os.getenv("ADMIN_ID") or "")
    db_path = (os.getenv("DB_PATH") or "yuk_bot.db").strip() or "yuk_bot.db"
    tz = (os.getenv("TZ") or "Asia/Tashkent").strip() or "Asia/Tashkent"
    timer_tick = max(3, int(os.getenv("TIMER_TICK_SEC") or "5"))
    return {
        "token": token,
        "group_id": group_id,
        "admin_ids": admin_ids,
        "db_path": db_path,
        "tz": tz,
        "timer_tick": timer_tick,
    }


def is_admin(user_id: int | None) -> bool:
    if user_id is None:
        return False
    if not settings()["admin_ids"]:
        return False
    return int(user_id) in settings()["admin_ids"]


def has_admins() -> bool:
    return bool(settings()["admin_ids"])


def startup_warnings() -> list[str]:
    s = settings()
    warnings: list[str] = []
    if not s["admin_ids"]:
        warnings.append("ADMIN_ID yoki ADMIN_IDS sozlanmagan — mas'ul funksiyalari o‘chiq")
    if not s["group_id"]:
        warnings.append("GROUP_ID sozlanmagan — guruhga e’lon yuborilmaydi")
    return warnings


def railway_setup_hint(user_id: int) -> str:
    return (
        "⚙️ <b>Bot sozlash kerak</b>\n\n"
        "Railway → <b>Variables</b> ga qo‘shing:\n\n"
        f"<code>ADMIN_ID={user_id}</code>\n"
        "<code>GROUP_ID=...</code> <i>(guruhda /id)</i>\n"
        "<code>BOT_TOKEN=...</code>\n\n"
        "Saqlang → <b>Redeploy</b> → botda qayta /start"
    )
