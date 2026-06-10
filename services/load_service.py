"""Guruhga yuborish, xabarlarni yangilash, hisobot."""

from __future__ import annotations

import logging
from typing import Any, Callable, Awaitable

from aiogram import Bot
from aiogram.types import InputMediaPhoto, Message, ReplyParameters

from config import get_group_id
from db import (
    get_active_session,
    get_participant,
    get_session,
    list_finished_sessions_by_day,
    list_participants,
    update_session,
)
from keyboards import group_join_closed, group_join_keyboard, personal_timer_keyboard
from services.group_check import GroupConfigError, verify_group_access
from time_util import now_iso
from timer_util import work_seconds
from ui import (
    group_load_card,
    media_caption_end,
    media_caption_start,
    personal_timer_card,
    ranking_block,
)
from yordamchi_push import push_to_yordamchi_hub, push_to_yordamchi_hub_background, today_iso

log = logging.getLogger(__name__)


def _daily_seconds_by_user(day_iso: str) -> dict[int, int]:
    totals: dict[int, int] = {}
    for s in list_finished_sessions_by_day(day_iso):
        sid = int(s.get("id") or 0)
        finished_iso = s.get("finished_at") or now_iso()
        if not sid:
            continue
        for p in list_participants(sid):
            uid = int(p.get("user_id") or 0)
            if not uid:
                continue
            sec = work_seconds(p, until_iso=finished_iso)
            totals[uid] = totals.get(uid, 0) + max(0, int(sec))
    return totals


async def backfill_hub_summaries(day_iso: str | None = None) -> tuple[int, int]:
    """
    Tugagan yuk sessiyalaridan xodimlar bo'yicha jami vaqtni hub'ga qayta yuboradi.
    Hech qanday guruh xabari yubormaydi.
    """
    day = (day_iso or today_iso()).strip()[:10]
    totals = _daily_seconds_by_user(day)
    sent = 0
    for uid, sec in totals.items():
        if sec <= 0:
            continue
        ok, via = await push_to_yordamchi_hub(
            tg_id=uid,
            bot_key="yuk",
            summary=f"Yuk (bugun jami): ish vaqti {sec} soniya",
            day_iso=day,
        )
        if ok:
            sent += 1
        else:
            log.warning("yuk hub backfill failed uid=%s: %s", uid, via)
    if totals:
        log.info("yuk hub backfill: %s/%s users for %s", sent, len(totals), day)
    return sent, len(totals)


async def backfill_today_hub_summaries() -> tuple[int, int]:
    return await backfill_hub_summaries(today_iso())


def _user_yuk_seconds_today(
    user_id: int, day_iso: str, *, include_active_sid: int | None = None
) -> int:
    """Bugungi tugagan yuklar + (ixtiyoriy) faol sessiyadagi jonli vaqt."""
    sec = _daily_seconds_by_user(day_iso).get(int(user_id), 0)
    if not include_active_sid:
        return sec
    session = get_session(int(include_active_sid))
    if not session or session.get("status") != "active":
        return sec
    for p in list_participants(int(include_active_sid)):
        if int(p.get("user_id") or 0) != int(user_id):
            continue
        sec += max(0, int(work_seconds(p)))
    return sec


async def push_live_session_hub(session_id: int) -> int:
    """Faol yuk davomida analytics uchun jonli vaqtni hub'ga yuboradi."""
    session = get_session(session_id)
    if not session or session.get("status") != "active":
        return 0
    day = today_iso()
    sent = 0
    for p in list_participants(session_id):
        uid = int(p.get("user_id") or 0)
        if not uid:
            continue
        sec = _user_yuk_seconds_today(uid, day, include_active_sid=session_id)
        if sec <= 0:
            continue
        ok, via = await push_to_yordamchi_hub(
            tg_id=uid,
            bot_key="yuk",
            summary=f"Yuk (bugun jami): ish vaqti {sec} soniya",
            day_iso=day,
        )
        if ok:
            sent += 1
        else:
            log.debug("yuk live hub uid=%s: %s", uid, via)
    return sent


def _reply_params(chat_id: int, message_id: int | None) -> ReplyParameters | None:
    if not message_id:
        return None
    return ReplyParameters(message_id=int(message_id), chat_id=int(chat_id))


def _album_first_id(session: dict[str, Any]) -> int | None:
    mid = session.get("group_album_msg_id")
    if mid:
        return int(mid)
    raw = session.get("group_album_msg_ids")
    if raw:
        part = str(raw).split(",")[0].strip()
        if part.isdigit():
            return int(part)
    return None


async def _send_with_reply_chain(
    bot: Bot,
    *,
    chat_id: int,
    reply_targets: list[int | None],
    send_fn: Callable[..., Awaitable[Message]],
    **send_kw: Any,
) -> Message:
    """Bir nechta xabarga reply urinish; oxirida replysiz."""
    send_kw.setdefault("chat_id", chat_id)
    for target in reply_targets:
        if not target:
            continue
        rp = _reply_params(chat_id, target)
        if not rp:
            continue
        try:
            return await send_fn(reply_parameters=rp, **send_kw)
        except Exception as e:
            log.warning(
                "reply chat=%s target=%s failed: %s", chat_id, target, e
            )
    return await send_fn(**send_kw)


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


def _build_session_photo_album(
    session: dict[str, Any], session_id: int
) -> list[InputMediaPhoto]:
    """4 ta surat: boshlanish + yakun (bitta albom)."""
    specs: list[tuple[str, str]] = [
        ("car_photo_start", media_caption_start("car", session_id)),
        ("unload_photo_start", media_caption_start("extra", session_id)),
        ("car_photo_end", media_caption_end("car")),
        ("unload_photo_end", media_caption_end("extra")),
    ]
    media: list[InputMediaPhoto] = []
    for field, caption in specs:
        file_id = session.get(field)
        if not file_id:
            continue
        media.append(
            InputMediaPhoto(media=file_id, caption=caption, parse_mode="HTML")
        )
    if media:
        media[0] = InputMediaPhoto(
            media=media[0].media,
            caption=f"📸  <b>YUK #{session_id}</b>  ·  boshlanish + yakun",
            parse_mode="HTML",
        )
        for i in range(1, len(media)):
            media[i] = InputMediaPhoto(media=media[i].media, parse_mode="HTML")
    return media


async def _send_session_photos(
    bot: Bot,
    *,
    chat_id: int,
    session: dict[str, Any],
    session_id: int,
) -> bool:
    """Guruhga barcha suratlar albomi; muvaffaqiyatsiz bo'lsa alohida yuborish."""
    album = _build_session_photo_album(session, session_id)
    if len(album) < 2:
        log.error(
            "session %s: suratlar yetarli emas (car_end=%s unload_end=%s)",
            session_id,
            bool(session.get("car_photo_end")),
            bool(session.get("unload_photo_end")),
        )
        singles = [
            session.get("car_photo_end"),
            session.get("unload_photo_end"),
        ]
        sent = False
        for fid in singles:
            if not fid:
                continue
            try:
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=fid,
                    caption=f"🏁  <b>YAKUN</b>  ·  #{session_id}",
                    parse_mode="HTML",
                )
                sent = True
            except Exception as e:
                log.error("yakun send_photo %s: %s", session_id, e)
        if not sent:
            await bot.send_message(
                chat_id=chat_id,
                text=f"⚠️  <b>#{session_id}</b> — yakun suratlari yuborilmadi.",
                parse_mode="HTML",
            )
        return sent

    try:
        await bot.send_media_group(chat_id=chat_id, media=album[:10])
        return True
    except Exception as e:
        log.error("suratlar albomi %s: %s", session_id, e)
        for item in album:
            try:
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=item.media,
                    parse_mode="HTML",
                )
            except Exception as e2:
                log.error("send_photo fallback %s: %s", session_id, e2)
        return False


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

    if first_id:
        status_msg = await _send_with_reply_chain(
            bot,
            chat_id=group_id,
            reply_targets=[first_id],
            send_fn=bot.send_message,
            text=status_text,
            parse_mode="HTML",
            reply_markup=group_join_keyboard(session_id),
        )
    else:
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
        "session %s: albom=%s status=%s (status→albom reply)",
        session_id,
        first_id,
        status_msg.message_id,
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

    session = get_session(session_id) or session

    await refresh_group_status(bot, session_id, phase="completed")

    await _send_session_photos(
        bot, chat_id=group_id, session=session, session_id=session_id
    )

    report_text = ranking_block(participants, finished_iso=finished_iso)
    await bot.send_message(
        chat_id=group_id,
        text=report_text,
        parse_mode="HTML",
    )

    for p in participants:
        uid = int(p.get("user_id") or 0)
        if not uid:
            continue
        day = (finished_iso or "")[:10] or today_iso()
        sec = work_seconds(p, until_iso=finished_iso)
        daily_totals = _daily_seconds_by_user(day)
        sec = max(sec, daily_totals.get(uid, 0))
        if sec <= 0:
            continue
        push_to_yordamchi_hub_background(
            tg_id=uid,
            bot_key="yuk",
            summary=f"Yuk (bugun jami): ish vaqti {sec} soniya",
            day_iso=day,
        )


def active_session_for_user(user_id: int) -> dict[str, Any] | None:
    s = get_active_session()
    if not s:
        return None
    if s.get("masul_id") == user_id:
        return s
    return s if s.get("status") == "active" else s
