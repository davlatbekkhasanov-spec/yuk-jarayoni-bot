"""Umumiy: /start, /id, bekor."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import has_admins, is_admin, railway_setup_hint, settings
from db import get_active_session
from keyboards import masul_main_menu
from ui import masul_welcome

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    name = message.from_user.full_name if message.from_user else "Foydalanuvchi"

    uid = message.from_user.id if message.from_user else None

    if not has_admins() and message.chat.type == "private" and uid:
        await message.answer(railway_setup_hint(uid), parse_mode="HTML")
        return

    if is_admin(uid):
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
    uid = message.from_user.id if message.from_user else "—"
    extra = ""
    if message.chat.type == "private" and not has_admins() and uid != "—":
        extra = (
            f"\n\n⚙️ Railway uchun:\n"
            f"<code>ADMIN_ID={uid}</code>"
        )
    await message.answer(
        f"📌 <b>Chat ID</b>\n<code>{message.chat.id}</code>\n\n"
        f"👤 <b>Sizning ID</b>\n<code>{uid}</code>{extra}",
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
    if not settings()["token"]:
        return "BOT_TOKEN sozlanmagan"
    return None
