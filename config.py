"""Muhit o‘zgaruvchilari."""

from __future__ import annotations

import os
from functools import lru_cache

from persist_data import bootstrap_persistence, resolve_db_path

_DB_BOOT = bootstrap_persistence(
    resolve_db_path(default_filename="yuk_bot.db"),
    legacy_names=("yuk_bot.db",),
)
_RESOLVED_DB_PATH = _DB_BOOT["db_path"]


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


def _parse_group_id(raw: str) -> int | None:
    raw = (raw or "").strip().strip('"').strip("'").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


_resolved_group_id: int | None = None


def get_group_id() -> int | None:
    """Yuborish uchun guruh ID (avto-supergroup tuzatishdan keyin)."""
    if _resolved_group_id is not None:
        return _resolved_group_id
    return settings()["group_id"]


def set_resolved_group_id(group_id: int) -> None:
    global _resolved_group_id
    _resolved_group_id = int(group_id)


def _resolve_group_id_from_env() -> int | None:
    for key in ("GROUP_ID", "GROUP_CHAT_ID", "CHAT_ID", "TELEGRAM_GROUP_ID"):
        val = _parse_group_id(os.getenv(key) or "")
        if val is not None:
            return val
    return None


def masul_ids_from_env() -> frozenset[int]:
    """Deploydan keyin qayta tiklanadigan mas'ullar (Railway Variables)."""
    return _parse_ids(os.getenv("MASUL_IDS") or os.getenv("OPERATOR_IDS") or "")


def persistent_operator_ids() -> frozenset[int]:
    """Har deployda avtomatik operators jadvaliga yoziladi."""
    return settings()["admin_ids"] | masul_ids_from_env()


@lru_cache(maxsize=1)
def settings():
    token = (os.getenv("BOT_TOKEN") or "").strip()
    group_id = _resolve_group_id_from_env()
    admin_ids = _parse_ids(os.getenv("ADMIN_IDS") or os.getenv("ADMIN_ID") or "")
    db_path = _RESOLVED_DB_PATH
    tz = (os.getenv("TZ") or "Asia/Tashkent").strip() or "Asia/Tashkent"
    timer_tick = max(3, int(os.getenv("TIMER_TICK_SEC") or "5"))
    return {
        "token": token,
        "group_id": group_id,
        "admin_ids": admin_ids,
        "masul_ids": masul_ids_from_env(),
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
        warnings.append("ADMIN_ID yoki ADMIN_IDS sozlanmagan — mas'ul funksiyalari o'chiq")
    if not s["group_id"]:
        warnings.append("GROUP_ID sozlanmagan — guruhga e'lon yuborilmaydi")
    return warnings


def railway_setup_hint(user_id: int) -> str:
    return (
        "⚙️ <b>Bot sozlash kerak</b>\n\n"
        "Railway → <b>Variables</b> ga qo'shing:\n\n"
        f"<code>ADMIN_ID={user_id}</code>\n"
        "<code>GROUP_ID=...</code> <i>(guruhda /id)</i>\n"
        "<code>BOT_TOKEN=...</code>\n\n"
        "Saqlang → <b>Redeploy</b> → botda qayta /start"
    )
