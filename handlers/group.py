"""Guruh va qatnashuvchi: qatnashish, tanaffus."""

from __future__ import annotations

import logging

from aiogram import Bot, Router
from aiogram.types import CallbackQuery

from callbacks import JoinCb, PauseCb
from db import (
    add_participant,
    get_participant,
    get_session,
    list_participants,
    participant_exists,
    pause_participant,
    resume_participant,
    update_participant_personal_msg,
)
from keyboards import personal_timer_keyboard
from services.load_service import push_live_session_hub, refresh_group_status
from ui import personal_timer_card
from yordamchi_push import push_session_start_background, push_session_update_background

router = Router()
log = logging.getLogger(__name__)


async def _send_or_update_personal(bot: Bot, session_id: int, user_id: int) -> bool:
    session = get_session(session_id)
    p = get_participant(session_id, user_id)
    if not session or not p:
        return False
    text = personal_timer_card(session=session, participant=p)
    markup = personal_timer_keyboard(session_id, paused=bool(p.get("paused_at")))
    msg_id = p.get("personal_msg_id")
    try:
        if msg_id:
            await bot.edit_message_text(
                text=text,
                chat_id=user_id,
                message_id=msg_id,
                parse_mode="HTML",
                reply_markup=markup,
            )
        else:
            sent = await bot.send_message(
                chat_id=user_id,
                text=text,
                parse_mode="HTML",
                reply_markup=markup,
            )
            update_participant_personal_msg(session_id, user_id, sent.message_id)
        return True
    except Exception as e:
        log.warning("personal timer uid=%s: %s", user_id, e)
        return False


@router.callback_query(JoinCb.filter())
async def on_join(callback: CallbackQuery, callback_data: JoinCb, bot: Bot) -> None:
    if callback_data.closed:
        await callback.answer("🔒 Yuk yakunlangan", show_alert=True)
        return

    session = get_session(callback_data.session_id)
    if not session or session.get("status") != "active":
        await callback.answer("⚠️ Bu yuk faol emas", show_alert=True)
        return

    user = callback.from_user
    if participant_exists(callback_data.session_id, user.id):
        await callback.answer(
            "✅ Siz ro'yxatdasiz — shaxsiy chatda tanaffus/davom tugmalari",
            show_alert=True,
        )
        return

    name = user.full_name or user.username or str(user.id)
    username = user.username or ""

    added = add_participant(
        session_id=callback_data.session_id,
        user_id=user.id,
        user_name=name,
        username=username,
    )
    if not added:
        await callback.answer("✅ Allaqachon ro'yxatda", show_alert=True)
        return

    if not await _send_or_update_personal(bot, callback_data.session_id, user.id):
        await callback.answer(
            "⚠️ Bot bilan shaxsiy chatda /start bosing, keyin qayta qatnashing",
            show_alert=True,
        )
        return

    push_session_start_background(
        tg_id=user.id,
        bot_key="yuk",
        user_name=name,
        activity_type="yuk",
        metadata={"session_id": int(callback_data.session_id)},
    )

    await refresh_group_status(bot, callback_data.session_id)
    await callback.answer("✅ Qatnashdingiz! Shaxsiy chatda taymer ochiq", show_alert=False)


@router.callback_query(PauseCb.filter())
async def on_pause_toggle(
    callback: CallbackQuery, callback_data: PauseCb, bot: Bot
) -> None:
    user = callback.from_user
    session = get_session(callback_data.session_id)
    if not session or session.get("status") != "active":
        await callback.answer("⚠️ Yuk faol emas", show_alert=True)
        return

    if not participant_exists(callback_data.session_id, user.id):
        await callback.answer("Avval qatnashing tugmasini bosing", show_alert=True)
        return

    action = callback_data.action
    if action == "pause":
        ok = pause_participant(callback_data.session_id, user.id)
        if not ok:
            await callback.answer("⏸ Allaqachon tanaffusda", show_alert=True)
            return
        await callback.answer("⏸ Tanaffus — taymer to'xtadi")
    elif action == "resume":
        ok = resume_participant(callback_data.session_id, user.id)
        if not ok:
            await callback.answer("▶️ Allaqachon ishlayapsiz", show_alert=True)
            return
        await callback.answer("▶️ Davom etildi")
    else:
        await callback.answer()
        return

    st = "paused" if action == "pause" else "active"
    push_session_update_background(
        tg_id=user.id,
        bot_key="yuk",
        user_name=user.full_name or user.username or "",
        activity_type="yuk",
        status=st,
        metadata={"session_id": int(callback_data.session_id)},
    )

    await _send_or_update_personal(bot, callback_data.session_id, user.id)
    await refresh_group_status(bot, callback_data.session_id)
