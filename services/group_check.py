"""Guruh ulanishini tekshirish."""

from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from config import get_group_id, set_resolved_group_id, settings

log = logging.getLogger(__name__)


class GroupConfigError(Exception):
    """GROUP_ID yoki bot huquqlari noto'g'ri."""


def supergroup_id_candidate(group_id: int) -> int | None:
    s = str(group_id)
    if s.startswith("-") and not s.startswith("-100"):
        return int("-100" + s[1:])
    return None


def group_id_candidates(group_id: int) -> list[int]:
    out: list[int] = [group_id]
    alt = supergroup_id_candidate(group_id)
    if alt is not None and alt not in out:
        out.append(alt)
    return out


def parse_group_id_hint() -> str:
    gid = settings()["group_id"]
    if gid is None:
        return (
            "Railway da <code>GROUP_ID</code> yo'q.\n"
            "<i>«Chat ID» nomli alohida o'zgaruvchi o'qilmaydi — "
            "qiymatni <code>GROUP_ID</code> ga yozing.</i>"
        )
    lines = [f"Hozirgi <code>GROUP_ID={gid}</code>"]
    alt = supergroup_id_candidate(gid)
    if alt:
        lines.append(f"Sinab ko'ring: <code>GROUP_ID={alt}</code>")
    resolved = get_group_id()
    if resolved and resolved != gid:
        lines.append(f"Ishlayotgan ID: <code>{resolved}</code>")
    return "\n".join(lines)


def group_fix_message(*, detail: str = "") -> str:
    from ui import banner, block_quote

    hint = parse_group_id_hint()
    extra = f"\n\n<i>{detail}</i>" if detail else ""
    return (
        f"{banner('ULANISH XATOSI', icon='⚠️')}\n\n"
        f"{block_quote('Guruhga yuborib bo\'lmadi')}\n\n"
        "<b>Telegram «chat not found» degani:</b>\n"
        "• <code>GROUP_ID</code> noto'g'ri (shaxsiy ID emas)\n"
        "• Bot guruhda yo'q\n"
        "• Bot guruhdan chiqarilgan\n\n"
        "<b>Qanday tuzatish:</b>\n"
        "1️⃣ Botni ishchi guruhga qo'shing\n"
        "2️⃣ Guruhda <code>/id</code> — Chat ID ni oling\n"
        "   (odatda <code>-100...</code> bilan boshlanadi)\n"
        "3️⃣ Railway → faqat <code>GROUP_ID</code>\n"
        "4️⃣ <b>Redeploy</b>\n\n"
        f"{hint}{extra}"
    )


async def verify_group_access(bot: Bot) -> str:
    configured = settings()["group_id"]
    if not configured:
        raise GroupConfigError("GROUP_ID sozlanmagan")

    last_err: Exception | None = None
    for chat_id in group_id_candidates(configured):
        try:
            chat = await bot.get_chat(chat_id)
            set_resolved_group_id(chat_id)
            if chat_id != configured:
                log.info(
                    "GROUP_ID %s o'rniga supergroup ID: %s",
                    configured,
                    chat_id,
                )
            return chat.title or chat.full_name or str(chat_id)
        except TelegramBadRequest as e:
            last_err = e
            if "chat not found" not in str(e).lower():
                raise GroupConfigError(str(e)) from e
        except TelegramForbiddenError as e:
            raise GroupConfigError("bot blocked or not in group") from e

    raise GroupConfigError("chat not found") from last_err
