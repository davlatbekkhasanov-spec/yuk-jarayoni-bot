"""Guruhga yuborish, xabarlarni yangilash, hisobot."""

from __future__ import annotations

import logging
from typing import Any

from aiogram import Bot
from aiogram.types import InputMediaPhoto

from config import get_group_id, settings
from services.group_check import GroupConfigError, verify_group_access
from db import (
    get_active_session,
    get_participant,
    get_session,
    list_participants,
    update_session,
)
from keyboards import group_join_closed, group_join_keyboard, personal_timer_keyboard
from time_util import now_iso
from ui import final_report, group_load_card, personal_timer_card

log = logging.getLogger(__name__)


async def publish_load_to_group(bot: Bot, session_id: int) -> None:
    session = get_session(session_id)
    if not session:
        raise ValueError("session not found")
    await verify_group_access(bot)
    group_id = get_group_id()
    if not group_id:
        raise GroupConfigError("GROUP_ID sozlanmagan")

    media = [
        InputMediaPhoto(
            media=session["car_photo_start"],
            caption="🚛 <b>Машина</b> — бошланиш",
            parse_mode="HTML",
        ),
        InputMediaPhoto(
            media=session["unload_photo_start"],
            caption="📍 <b>Тушириш жойи</b> — бошланиш",
            parse_mode="HTML",
        ),
    ]
    album = await bot.send_media_group(chat_id=group_id, media=media)

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
        group_album_msg_id=album[0].message_id if album else None,
        group_status_msg_id=status_msg.message_id,
        started_at=now_iso(),
    )


async def refresh_group_status(bot: Bot, session_id: int, *, phase: str = "active") -> None:
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
    markup = (
        group_join_closed(session_id)
        if status in ("finishing", "completed")
        else group_join_keyboard(session_id)
    )

    try:
        await bot.edit_message_text(
            text=text,
            chat_id=chat_id,
            message_id=msg_id,
            parse_mode="HTML",
            reply_markup=markup,
        )
    except Exception as e:
        log.debug("edit group status: %s", e)


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
    report_text = final_report(session=session, participants=participants)

    media = []
    if session.get("car_photo_start"):
        media.append(
            InputMediaPhoto(
                media=session["car_photo_start"],
                caption="🚛 Бошланиш — машина",
            )
        )
    if session.get("unload_photo_start"):
        media.append(
            InputMediaPhoto(media=session["unload_photo_start"], caption="📍 Бошланиш — жой")
        )
    if session.get("car_photo_end"):
        media.append(InputMediaPhoto(media=session["car_photo_end"], caption="🚛 Якун — машина"))
    if session.get("unload_photo_end"):
        media.append(
            InputMediaPhoto(media=session["unload_photo_end"], caption="📍 Якун — жой")
        )

    if media:
        media[0].caption = report_text
        media[0].parse_mode = "HTML"
        await bot.send_media_group(chat_id=group_id, media=media[:10])
    else:
        await bot.send_message(
            chat_id=group_id,
            text=report_text,
            parse_mode="HTML",
        )

    await refresh_group_status(bot, session_id, phase="finishing")


def active_session_for_user(user_id: int) -> dict[str, Any] | None:
    s = get_active_session()
    if not s:
        return None
    if s.get("masul_id") == user_id:
        return s
    return s if s.get("status") == "active" else s
