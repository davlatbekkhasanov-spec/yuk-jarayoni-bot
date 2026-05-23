"""Guruh: qatnashish tugmasi."""

from __future__ import annotations

import logging

from aiogram import Bot, Router
from aiogram.types import CallbackQuery

from callbacks import JoinCb
from db import (
    add_participant,
    get_session,
    list_participants,
    participant_exists,
    update_participant_personal_msg,
)
from services.load_service import refresh_group_status
from ui import personal_timer_card

router = Router()
log = logging.getLogger(__name__)


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
        await callback.answer("✅ Siz allaqachon qatnashgansiz", show_alert=True)
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
        await callback.answer("✅ Allaqachon ro‘yxatda", show_alert=True)
        return

    parts = list_participants(callback_data.session_id)
    me = next((p for p in parts if p["user_id"] == user.id), None)
    joined_at = (me or {}).get("joined_at") or ""

    try:
        personal = await bot.send_message(
            chat_id=user.id,
            text=personal_timer_card(
                session=session,
                user_name=name,
                joined_at=joined_at,
            ),
            parse_mode="HTML",
        )
        update_participant_personal_msg(
            callback_data.session_id, user.id, personal.message_id
        )
    except Exception as e:
        log.warning("personal timer DM failed uid=%s: %s", user.id, e)
        await callback.answer(
            "⚠️ Bot bilan shaxsiy chatda /start bosing, keyin qayta «Қатнашиш»",
            show_alert=True,
        )
        return

    await refresh_group_status(bot, callback_data.session_id)
    await callback.answer("✅ Қатнашдингиз! Shaxsiy chatda tаймер ochiq", show_alert=False)
