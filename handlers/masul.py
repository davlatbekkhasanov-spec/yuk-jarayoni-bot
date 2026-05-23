"""Mas'ul: yuk boshlash, yakunlash, fotolar."""

from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from callbacks import FinishCb
from config import has_admins, is_admin, railway_setup_hint, settings
from db import (
    create_session,
    get_active_session,
    get_session,
    list_participants,
    update_session,
)
from keyboards import cancel_inline, masul_finish_confirm, masul_main_menu
from services.group_check import GroupConfigError, group_fix_message, verify_group_access
from services.load_service import publish_final_report, publish_load_to_group, refresh_group_status
from states import LoadFinishStates, LoadStartStates
from time_util import now_iso
from ui import masul_status_panel, photo_prompt

router = Router()
log = logging.getLogger(__name__)


def _admin_only(message: Message) -> bool:
    return is_admin(message.from_user.id if message.from_user else None)


async def _require_masul(message: Message) -> bool:
    uid = message.from_user.id if message.from_user else None
    if not has_admins():
        if uid:
            await message.answer(railway_setup_hint(uid), parse_mode="HTML")
        return False
    if not is_admin(uid):
        await message.answer("⚠️ Bu bo‘lim faqat <b>mas'ul</b> uchun.", parse_mode="HTML")
        return False
    return True


@router.message(F.text == "🚚 Юк келди", F.chat.type == "private")
async def start_load_flow(message: Message, state: FSMContext) -> None:
    if not await _require_masul(message):
        return

    if not settings()["group_id"]:
        await message.answer(
            "⚠️ <b>GROUP_ID</b> sozlanmagan.\n"
            "Guruhda /id oling va Railway Variables ga qo‘ying.",
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
            reply_markup=masul_main_menu(can_finish=active.get("status") == "active"),
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
            "🚛 Машина фотоси",
            "Yuk kelgan mashinani to‘liq ko‘rinadigan qilib surating",
        ),
        parse_mode="HTML",
        reply_markup=cancel_inline(),
    )


@router.message(LoadStartStates.car_photo, F.photo, F.chat.type == "private")
async def start_car_photo(message: Message, state: FSMContext) -> None:
    if not await _require_masul(message):
        return
    data = await state.get_data()
    sid = data.get("session_id")
    file_id = message.photo[-1].file_id
    update_session(sid, car_photo_start=file_id)
    await state.set_state(LoadStartStates.unload_photo)
    await message.answer(
        photo_prompt(
            2,
            2,
            "📍 Тушириладиган жой",
            "Tovar tushiriladigan joyni aniq ko‘rsating",
        ),
        parse_mode="HTML",
        reply_markup=cancel_inline(),
    )


@router.message(LoadStartStates.unload_photo, F.photo, F.chat.type == "private")
async def start_unload_photo(message: Message, state: FSMContext, bot: Bot) -> None:
    if not await _require_masul(message):
        return
    data = await state.get_data()
    sid = int(data.get("session_id"))
    file_id = message.photo[-1].file_id
    update_session(sid, unload_photo_start=file_id)

    try:
        await publish_load_to_group(bot, sid)
    except GroupConfigError as e:
        log.warning("publish_load group: %s", e)
        from db import abandon_session

        abandon_session(sid)
        await message.answer(group_fix_message(detail=str(e)), parse_mode="HTML")
        await state.clear()
        return
    except Exception as e:
        log.exception("publish_load")
        from db import abandon_session

        abandon_session(sid)
        await message.answer(
            group_fix_message(detail=str(e)[:200]),
            parse_mode="HTML",
        )
        await state.clear()
        return

    await state.clear()
    await message.answer(
        "✅ <b>Юк гуруҳга e’lon qilindi!</b>\n\n"
        "👷 Ishchilar <b>Қатнашиш</b> bosadi — tаймерlar ishga tushadi.\n"
        "Tayyor bo‘lgach <b>🏁 Якунлаш</b> ni bosing.",
        parse_mode="HTML",
        reply_markup=masul_main_menu(can_finish=True),
    )


@router.message(F.text == "📊 Ҳолат", F.chat.type == "private")
async def status_panel(message: Message) -> None:
    if not await _require_masul(message):
        return
    active = get_active_session()
    parts = list_participants(active["id"]) if active else []
    await message.answer(
        masul_status_panel(active, parts),
        parse_mode="HTML",
        reply_markup=masul_main_menu(
            can_finish=bool(active and active.get("status") == "active")
        ),
    )


@router.message(F.text == "🏁 Якунлаш", F.chat.type == "private")
async def finish_prompt(message: Message) -> None:
    if not await _require_masul(message):
        return
    active = get_active_session()
    if not active or active.get("status") != "active":
        await message.answer(
            "⚠️ Faol yuk yo‘q.",
            reply_markup=masul_main_menu(can_finish=False),
        )
        return
    if active.get("masul_id") != message.from_user.id:
        await message.answer("⚠️ Faqat sessiya ochgan mas'ul yakunlay oladi.")
        return

    parts = list_participants(active["id"])
    await message.answer(
        f"🏁 <b>Юк #{active['id']} ni yakunlaysizmi?</b>\n\n"
        f"👷 Qatnashuvchilar: <b>{len(parts)}</b>\n\n"
        "Tasdiqlangach — oxirgi 2 ta foto va avtomatik <b>отчёт</b>.",
        parse_mode="HTML",
        reply_markup=masul_finish_confirm(active["id"]),
    )


@router.callback_query(FinishCb.filter(F.confirm == 1))
async def finish_confirmed(
    callback: CallbackQuery, callback_data: FinishCb, state: FSMContext, bot: Bot
) -> None:
    if not is_admin(callback.from_user.id):
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
        photo_prompt(1, 2, "🚛 Машина — якун", "Yuk tugagach mashina holati"),
        parse_mode="HTML",
        reply_markup=cancel_inline(),
    )
    await callback.answer()


@router.callback_query(FinishCb.filter(F.confirm == 0))
async def finish_cancel(callback: CallbackQuery) -> None:
    await callback.message.edit_text("↩️ Yakunlash bekor qilindi.")
    await callback.answer()


@router.message(LoadFinishStates.car_photo, F.photo, F.chat.type == "private")
async def finish_car_photo(message: Message, state: FSMContext) -> None:
    if not await _require_masul(message):
        return
    data = await state.get_data()
    sid = data.get("session_id")
    update_session(sid, car_photo_end=message.photo[-1].file_id)
    await state.set_state(LoadFinishStates.unload_photo)
    await message.answer(
        photo_prompt(2, 2, "📍 Тушириш жойи — якун", "Ish tugagach joy holati"),
        parse_mode="HTML",
        reply_markup=cancel_inline(),
    )


@router.message(LoadFinishStates.unload_photo, F.photo, F.chat.type == "private")
async def finish_unload_photo(message: Message, state: FSMContext, bot: Bot) -> None:
    if not await _require_masul(message):
        return
    data = await state.get_data()
    sid = int(data.get("session_id"))
    update_session(sid, unload_photo_end=message.photo[-1].file_id, status="completed", finished_at=now_iso())

    await publish_final_report(bot, sid)
    await state.clear()

    await message.answer(
        "✅ <b>Отчёт guruhga yuborildi!</b>\n\nYangi yuk uchun <b>🚚 Юк келди</b> bosing.",
        parse_mode="HTML",
        reply_markup=masul_main_menu(can_finish=False),
    )


@router.message(LoadStartStates.car_photo)
@router.message(LoadStartStates.unload_photo)
@router.message(LoadFinishStates.car_photo)
@router.message(LoadFinishStates.unload_photo)
async def expect_photo(message: Message) -> None:
    if not await _require_masul(message):
        return
    await message.answer(
        "📸 Iltimos, <b>foto</b> yuboring (hujjat emas).",
        parse_mode="HTML",
        reply_markup=cancel_inline(),
    )
