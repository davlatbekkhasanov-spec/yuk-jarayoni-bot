"""Guruhga yuborish, xabarlarni yangilash, hisobot."""

from __future__ import annotations

import logging
from typing import Any

from aiogram import Bot
from aiogram.types import InputMediaPhoto, ReplyParameters

from config import get_group_id
from db import (
    get_active_session,
    get_participant,
    get_session,
    list_participants,
    update_session,
)
from kaizen import compute_kaizen
from keyboards import group_join_closed, group_join_keyboard, personal_timer_keyboard
from services.group_check import GroupConfigError, verify_group_access
from time_util import now_iso
from ui import (
    group_load_card,
    kaizen_block,
    media_caption_end,
    media_caption_start,
    personal_timer_card,
    ranking_block,
)

log = logging.getLogger(__name__)


def _album_reply_message_id(session: dict[str, Any]) -> int | None:
    """Boshlang'ich albomning birinchi surat xabari ID."""
    mid = session.get("group_album_msg_id")
    if mid:
        return int(mid)
    raw = session.get("group_album_msg_ids")
    if raw:
        part = str(raw).split(",")[0].strip()
        if part.isdigit():
            return int(part)
    return None


def _build_start_album(session: dict[str, Any], session_id: int) -> list[InputMediaPhoto]:
    media: list[InputMediaPhoto] = []
    if session.get("car_photo_start"):
        media.append(
            InputMediaPhoto(
                media=session["car_photo_start"],
                caption=media_caption_start("car", session_id),
                parse_mode="HTML",
            )
        )
    if session.get("unload_photo_start"):
        media.append(
            InputMediaPhoto(
                media=session["unload_photo_start"],
                caption=media_caption_start("extra", session_id),
                parse_mode="HTML",
            )
        )
    return media


async def _send_end_photos_reply(
    bot: Bot,
    *,
    chat_id: int,
    session: dict[str, Any],
    session_id: int,
) -> None:
    """
    Yakun suratlari — boshidagi albomga reply.
    Media group reply Telegramda ishonchsiz; alohida send_photo ishlatiladi.
    """
    reply_id = _album_reply_message_id(session)
    items: list[tuple[str, str]] = []
    if session.get("car_photo_end"):
        items.append(("car", session["car_photo_end"]))
    if session.get("unload_photo_end"):
        items.append(("extra", session["unload_photo_end"]))
    if not items:
        log.warning("session %s: yakun suratlari yo'q", session_id)
        return

    reply_params = (
        ReplyParameters(message_id=reply_id) if reply_id else None
    )
    if not reply_params:
        log.warning(
            "session %s: group_album_msg_id yo'q — reply bo'lmaydi", session_id
        )

    for i, (kind, file_id) in enumerate(items):
        if i == 0:
            caption = f"🏁  <b>YAKUN SURATLARI</b>  ·  #{session_id}"
        else:
            caption = media_caption_end(kind)

        kw: dict[str, Any] = {
            "chat_id": chat_id,
            "photo": file_id,
            "caption": caption,
            "parse_mode": "HTML",
        }
        if reply_params:
            kw["reply_parameters"] = reply_params

        try:
            await bot.send_photo(**kw)
        except Exception as e:
            log.warning(
                "yakun surat reply bilan yuborilmadi (kind=%s, reply=%s): %s",
                kind,
                reply_id,
                e,
            )
            kw.pop("reply_parameters", None)
            await bot.send_photo(**kw)


async def publish_load_to_group(bot: Bot, session_id: int) -> None:
    session = get_session(session_id)
    if not session:
        raise ValueError("session not found")
    await verify_group_access(bot)
    group_id = get_group_id()
    if not group_id:
        raise GroupConfigError("GROUP_ID sozlanmagan")

    media = _build_start_album(session, session_id)
    if not media:
        raise GroupConfigError("Suratlar topilmadi")

    album = await bot.send_media_group(chat_id=group_id, media=media[:10])
    album_ids = ",".join(str(m.message_id) for m in album)
    first_id = album[0].message_id if album else None

    status_text = group_load_card(session=session, participants=[], phase="active")
    status_msg = await bot.send_message(
        chat_id=group_id,
        text=status_text,
        parse_mode="HTML",
        reply_markup=group_join_keyboard(session_id),
    )

    update_session(
        session_id,
        status="active",
        group_chat_id=group_id,
        group_album_msg_id=first_id,
        group_album_msg_ids=album_ids,
        group_status_msg_id=status_msg.message_id,
        started_at=now_iso(),
    )
    log.info(
        "session %s: bosh albom msg_id=%s ids=%s",
        session_id,
        first_id,
        album_ids,
    )


async def refresh_group_status(
    bot: Bot, session_id: int, *, phase: str = "active"
) -> None:
    session = get_session(session_id)
    if not session:
        return
    chat_id = session.get("group_chat_id")
    msg_id = session.get("group_status_msg_id")
    if not chat_id or not msg_id:
        return

    participants = list_participants(session_id)
    text = group_load_card(session=session, participants=participants, phase=phase)
    status = session.get("status") or "active"
    if status in ("finishing", "completed"):
        markup = group_join_closed(session_id)
    else:
        markup = group_join_keyboard(session_id)

    try:
        await bot.edit_message_text(
            text=text,
            chat_id=chat_id,
            message_id=msg_id,
            parse_mode="HTML",
            reply_markup=markup,
        )
    except Exception as e:
        log.warning("edit group status #%s: %s", session_id, e)


async def refresh_personal_timer(bot: Bot, session_id: int, user_id: int) -> None:
    session = get_session(session_id)
    p = get_participant(session_id, user_id)
    if not session or not p or not p.get("personal_msg_id"):
        return
    text = personal_timer_card(session=session, participant=p)
    markup = personal_timer_keyboard(session_id, paused=bool(p.get("paused_at")))
    try:
        await bot.edit_message_text(
            text=text,
            chat_id=user_id,
            message_id=p["personal_msg_id"],
            parse_mode="HTML",
            reply_markup=markup,
        )
    except Exception as e:
        log.debug("edit personal timer uid=%s: %s", user_id, e)


async def refresh_personal_timers(bot: Bot, session_id: int) -> None:
    session = get_session(session_id)
    if not session or session.get("status") != "active":
        return

    for p in list_participants(session_id):
        if p.get("personal_msg_id"):
            await refresh_personal_timer(bot, session_id, int(p["user_id"]))


async def publish_final_report(bot: Bot, session_id: int) -> None:
    session = get_session(session_id)
    if not session:
        return
    group_id = session.get("group_chat_id") or get_group_id()
    if not group_id:
        return

    participants = list_participants(session_id)
    finished_iso = session.get("finished_at") or now_iso()
    m = compute_kaizen(
        session=session, participants=participants, finished_iso=finished_iso
    )

    # 1) Yakun suratlari — bosh albomga reply (avval, statusdan oldin)
    await _send_end_photos_reply(
        bot, chat_id=group_id, session=session, session_id=session_id
    )

    # 2) Status + Kaizen kartasi
    await refresh_group_status(bot, session_id, phase="completed")

    # 3) To'liq hisobot — status xabariga reply
    report_text = (
        f"{ranking_block(participants, finished_iso=finished_iso)}\n\n"
        f"{kaizen_block(m)}"
    )
    reply_status = session.get("group_status_msg_id")
    msg_kw: dict[str, Any] = {
        "chat_id": group_id,
        "text": report_text,
        "parse_mode": "HTML",
    }
    if reply_status:
        msg_kw["reply_parameters"] = ReplyParameters(message_id=int(reply_status))
    try:
        await bot.send_message(**msg_kw)
    except Exception as e:
        log.warning("hisobot reply bilan yuborilmadi: %s", e)
        msg_kw.pop("reply_parameters", None)
        await bot.send_message(**msg_kw)


def active_session_for_user(user_id: int) -> dict[str, Any] | None:
    s = get_active_session()
    if not s:
        return None
    if s.get("masul_id") == user_id:
        return s
    return s if s.get("status") == "active" else s
