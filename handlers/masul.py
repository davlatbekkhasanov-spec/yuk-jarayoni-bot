"""Mas'ul / operator: yuk boshlash, yakunlash, fotolar."""

from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from callbacks import FinishCb
from config import has_admins, is_admin, railway_setup_hint, settings
from db import (
    abandon_session,
    create_session,
    get_active_session,
    get_session,
    list_participants,
    update_session,
)
from keyboards import cancel_inline, masul_finish_confirm, masul_main_menu
from roles import can_manage_yuk
from services.group_check import GroupConfigError, group_fix_message, verify_group_access
from services.load_service import publish_final_report, publish_load_to_group, refresh_group_status
from states import LoadFinishStates, LoadStartStates
from texts import (
    BTN_HOLAT_ALL,
    BTN_YAKUNLASH_ALL,
    BTN_YUK_KELDI_ALL,
)
from time_util import now_iso
from ui import finish_success, masul_status_panel, photo_prompt, publish_success

router = Router()
log = logging.getLogger(__name__)


def _menu(uid: int, *, can_finish: bool):
    return masul_main_menu(
        can_finish=can_finish,
        show_staff=is_admin(uid),
    )


async def _require_operator(message: Message) -> bool:
    uid = message.from_user.id if message.from_user else None
    if not has_admins():
        if uid:
            await message.answer(railway_setup_hint(uid), parse_mode="HTML")
        return False
    if not can_manage_yuk(uid):
        await message.answer(
            "⚠️ Bu bo'lim faqat <b>mas'ul</b> uchun.\n\n"
            "<i>Asosiy admin sizni «Mas'ul qo'shish» orqali ro'yxatga oladi. "
            "Railway ga ID kerak emas.</i>",
            parse_mode="HTML",
        )
        return False
    return True


@router.message(F.text.in_(BTN_YUK_KELDI_ALL), F.chat.type == "private")
async def start_load_flow(message: Message, state: FSMContext) -> None:
    if not await _require_operator(message):
        return

    if not settings()["group_id"]:
        await message.answer(
            "⚠️ <b>GROUP_ID</b> sozlanmagan.\n"
            "Guruhda /id oling va Railway Variables ga qo'ying.",
            parse_mode="HTML",
        )
        return

    try:
        await verify_group_access(message.bot)
    except GroupConfigError:
        await message.answer(group_fix_message(), parse_mode="HTML")
        return

    active = get_active_session()
    if active and active.get("status") in ("active", "finishing", "draft"):
        await message.answer(
            "⚠️ Avvalo joriy yukni yakunlang.",
            parse_mode="HTML",
            reply_markup=_menu(
                message.from_user.id,
                can_finish=active.get("status") == "active",
            ),
        )
        return

    masul_name = message.from_user.full_name if message.from_user else "Mas'ul"
    sid = create_session(
        masul_id=message.from_user.id,
        masul_name=masul_name,
    )
    await state.set_state(LoadStartStates.car_photo)
    await state.update_data(session_id=sid)

    await message.answer(
        photo_prompt(
            1,
            2,
            "🚛 Mashina fotosuri",
            "Yuk kelgan mashinani to'liq ko'rinadigan qilib surating",
        ),
        parse_mode="HTML",
        reply_markup=cancel_inline(),
    )


@router.message(LoadStartStates.car_photo, F.photo, F.chat.type == "private")
async def start_car_photo(message: Message, state: FSMContext) -> None:
    if not await _require_operator(message):
        return
    data = await state.get_data()
    sid = data.get("session_id")
    update_session(sid, car_photo_start=message.photo[-1].file_id)
    await state.set_state(LoadStartStates.extra_photo)
    await message.answer(
        photo_prompt(
            2,
            2,
            "➕ Qo'shimcha rasm",
            "Kerakli qo'shimcha surat (yorliq, hujjat, yuk holati va hokazo)",
        ),
        parse_mode="HTML",
        reply_markup=cancel_inline(),
    )


@router.message(LoadStartStates.extra_photo, F.photo, F.chat.type == "private")
async def start_extra_photo(message: Message, state: FSMContext, bot: Bot) -> None:
    if not await _require_operator(message):
        return
    data = await state.get_data()
    sid = int(data.get("session_id"))
    update_session(sid, unload_photo_start=message.photo[-1].file_id)

    try:
        await publish_load_to_group(bot, sid)
    except GroupConfigError as e:
        log.warning("publish_load group: %s", e)
        abandon_session(sid)
        await message.answer(group_fix_message(detail=str(e)), parse_mode="HTML")
        await state.clear()
        return
    except Exception as e:
        log.exception("publish_load")
        abandon_session(sid)
        await message.answer(
            group_fix_message(detail=str(e)[:200]),
            parse_mode="HTML",
        )
        await state.clear()
        return

    await state.clear()
    uid = message.from_user.id
    await message.answer(
        publish_success(sid),
        parse_mode="HTML",
        reply_markup=_menu(uid, can_finish=True),
    )


@router.message(F.text.in_(BTN_HOLAT_ALL), F.chat.type == "private")
async def status_panel(message: Message) -> None:
    if not await _require_operator(message):
        return
    active = get_active_session()
    parts = list_participants(active["id"]) if active else []
    uid = message.from_user.id
    await message.answer(
        masul_status_panel(active, parts),
        parse_mode="HTML",
        reply_markup=_menu(
            uid,
            can_finish=bool(active and active.get("status") == "active"),
        ),
    )


@router.message(F.text.in_(BTN_YAKUNLASH_ALL), F.chat.type == "private")
async def finish_prompt(message: Message) -> None:
    if not await _require_operator(message):
        return
    active = get_active_session()
    if not active or active.get("status") != "active":
        await message.answer(
            "⚠️ Faol yuk yo'q.",
            reply_markup=_menu(message.from_user.id, can_finish=False),
        )
        return

    parts = list_participants(active["id"])
    await message.answer(
        f"🏁 <b>Yuk #{active['id']} ni yakunlaysizmi?</b>\n\n"
        f"👷 Qatnashuvchilar: <b>{len(parts)}</b>\n\n"
        "Tasdiqlangach — mashina + qo'shimcha rasm va <b>hisobot</b>.",
        parse_mode="HTML",
        reply_markup=masul_finish_confirm(active["id"]),
    )


@router.callback_query(FinishCb.filter(F.confirm == 1))
async def finish_confirmed(
    callback: CallbackQuery, callback_data: FinishCb, state: FSMContext, bot: Bot
) -> None:
    if not can_manage_yuk(callback.from_user.id):
        await callback.answer("Faqat mas'ul", show_alert=True)
        return

    session = get_session(callback_data.session_id)
    if not session or session.get("status") != "active":
        await callback.answer("Sessiya topilmadi", show_alert=True)
        return

    update_session(callback_data.session_id, status="finishing")
    await refresh_group_status(bot, callback_data.session_id, phase="finishing")

    await callback.message.edit_text(
        "🏁 <b>Yakunlash boshlandi</b>",
        parse_mode="HTML",
    )
    await state.set_state(LoadFinishStates.car_photo)
    await state.update_data(session_id=callback_data.session_id)
    await callback.message.answer(
        photo_prompt(1, 2, "🚛 Mashina — yakun", "Yuk tugagach mashina holati"),
        parse_mode="HTML",
        reply_markup=cancel_inline(),
    )
    await callback.answer()


@router.callback_query(FinishCb.filter(F.confirm == 0))
async def finish_cancel(callback: CallbackQuery) -> None:
    await callback.message.edit_text("↩️ Yakunlash bekor qilindi.", parse_mode="HTML")
    await callback.answer()


@router.message(LoadFinishStates.car_photo, F.photo, F.chat.type == "private")
async def finish_car_photo(message: Message, state: FSMContext) -> None:
    if not await _require_operator(message):
        return
    data = await state.get_data()
    sid = data.get("session_id")
    update_session(sid, car_photo_end=message.photo[-1].file_id)
    await state.set_state(LoadFinishStates.extra_photo)
    await message.answer(
        photo_prompt(2, 2, "➕ Qo'shimcha rasm — yakun", "Kerakli qo'shimcha surat"),
        parse_mode="HTML",
        reply_markup=cancel_inline(),
    )


@router.message(LoadFinishStates.extra_photo, F.photo, F.chat.type == "private")
async def finish_extra_photo(message: Message, state: FSMContext, bot: Bot) -> None:
    if not await _require_operator(message):
        return
    data = await state.get_data()
    sid = int(data.get("session_id"))
    update_session(
        sid,
        unload_photo_end=message.photo[-1].file_id,
        status="completed",
        finished_at=now_iso(),
    )

    await publish_final_report(bot, sid)
    await state.clear()

    await message.answer(
        finish_success(),
        parse_mode="HTML",
        reply_markup=_menu(message.from_user.id, can_finish=False),
    )


@router.message(LoadStartStates.car_photo)
@router.message(LoadStartStates.extra_photo)
@router.message(LoadFinishStates.car_photo)
@router.message(LoadFinishStates.extra_photo)
async def expect_photo(message: Message) -> None:
    if not await _require_operator(message):
        return
    await message.answer(
        "📸 Iltimos, <b>foto</b> yuboring (hujjat emas).",
        parse_mode="HTML",
        reply_markup=cancel_inline(),
    )
