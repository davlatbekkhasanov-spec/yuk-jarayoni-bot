"""Umumiy: /start, /id, bekor."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import is_admin, settings
from db import get_active_session
from keyboards import masul_main_menu
from ui import masul_welcome

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    name = message.from_user.full_name if message.from_user else "Foydalanuvchi"

    if is_admin(message.from_user.id if message.from_user else None):
        active = get_active_session()
        can_finish = bool(active and active.get("status") == "active")
        await message.answer(
            masul_welcome(name),
            parse_mode="HTML",
            reply_markup=masul_main_menu(can_finish=can_finish),
        )
        return

    await message.answer(
        "👋 <b>Юк жараёни боти</b>\n\n"
        "Гуруҳда <b>✅ Қатнашиш</b> tugmasini bosing — shaxsiy tаймерingiz ochiladi.\n\n"
        "<i>Mas'ul: botga /start (admin ID sozlangan bo‘lishi kerak)</i>",
        parse_mode="HTML",
    )


@router.message(Command("id"))
async def cmd_id(message: Message) -> None:
    await message.answer(
        f"📌 <b>Chat ID</b>\n<code>{message.chat.id}</code>\n\n"
        f"👤 <b>Sizning ID</b>\n<code>{message.from_user.id if message.from_user else '—'}</code>",
        parse_mode="HTML",
    )


@router.callback_query(F.data == "ui:cancel")
async def ui_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    sid = data.get("session_id")
    if sid:
        from db import cancel_draft_session

        cancel_draft_session(int(sid))
    await state.clear()
    await callback.message.edit_text(
        "❌ <b>Бекор қилинди</b>",
        parse_mode="HTML",
    )
    if is_admin(callback.from_user.id):
        active = get_active_session()
        can_finish = bool(active and active.get("status") == "active")
        await callback.message.answer(
            "Menyuga qaytdingiz.",
            reply_markup=masul_main_menu(can_finish=can_finish),
        )
    await callback.answer()


def ensure_configured() -> str | None:
    s = settings()
    if not s["token"]:
        return "BOT_TOKEN sozlanmagan"
    if not s["admin_ids"]:
        return "ADMIN_ID yoki ADMIN_IDS sozlanmagan"
    return None
