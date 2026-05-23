"""Guruh ulanishini tekshirish."""

from __future__ import annotations

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from config import settings


class GroupConfigError(Exception):
    """GROUP_ID yoki bot huquqlari noto‘g‘ri."""


def parse_group_id_hint() -> str:
    gid = settings()["group_id"]
    if gid is None:
        return "GROUP_ID Railway da yo‘q yoki noto‘g‘ri format"
    return f"Hozirgi <code>GROUP_ID={gid}</code>"


def group_fix_message(*, detail: str = "") -> str:
    hint = parse_group_id_hint()
    extra = f"\n\n<i>{detail}</i>" if detail else ""
    return (
        "❌ <b>Guruhga yuborib bo‘lmadi</b>\n\n"
        "<b>Telegram «chat not found» degani:</b>\n"
        "• <code>GROUP_ID</code> noto‘g‘ri (shaxsiy ID emas!)\n"
        "• Bot guruhda yo‘q\n"
        "• Bot guruhdan chiqarilgan\n\n"
        "<b>Qanday tuzatish:</b>\n"
        "1️⃣ Botni <b>ishchi guruhga</b> qo‘shing\n"
        "2️⃣ Guruhda <code>/id</code> yuboring — <b>Chat ID</b> ni oling\n"
        "   (odatda <code>-100...</code> bilan boshlanadi)\n"
        "3️⃣ Railway → Variables → <code>GROUP_ID</code> ni shu raqamga almashtiring\n"
        "4️⃣ <b>Redeploy</b>\n\n"
        f"{hint}{extra}"
    )


async def verify_group_access(bot: Bot) -> str:
    """
    Guruh mavjudligi va bot huquqini tekshiradi.
    Muvaffaqiyatda guruh nomini qaytaradi.
    """
    group_id = settings()["group_id"]
    if not group_id:
        raise GroupConfigError("GROUP_ID sozlanmagan")

    try:
        chat = await bot.get_chat(group_id)
    except TelegramBadRequest as e:
        msg = str(e).lower()
        if "chat not found" in msg:
            raise GroupConfigError("chat not found") from e
        raise GroupConfigError(str(e)) from e
    except TelegramForbiddenError as e:
        raise GroupConfigError("bot blocked or not in group") from e

    title = chat.title or chat.full_name or str(group_id)
    return title
