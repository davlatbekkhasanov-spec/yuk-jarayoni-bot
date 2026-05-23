"""Umumiy: /start, /id, bekor."""

from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import get_group_id, has_admins, is_admin, railway_setup_hint, settings
from services.group_check import GroupConfigError, group_fix_message, parse_group_id_hint, verify_group_access
from db import get_active_session
from keyboards import masul_main_menu
from roles import can_manage_yuk
from ui import masul_welcome, worker_welcome, worker_welcome

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    name = message.from_user.full_name if message.from_user else "Foydalanuvchi"

    uid = message.from_user.id if message.from_user else None

    if not has_admins() and message.chat.type == "private" and uid:
        await message.answer(railway_setup_hint(uid), parse_mode="HTML")
        return

    if can_manage_yuk(uid):
        active = get_active_session()
        can_finish = bool(active and active.get("status") == "active")
        await message.answer(
            masul_welcome(name),
            parse_mode="HTML",
            reply_markup=masul_main_menu(
                can_finish=can_finish,
                show_staff=is_admin(uid),
            ),
        )
        return

    await message.answer(worker_welcome(), parse_mode="HTML")


@router.message(Command("id"))
async def cmd_id(message: Message) -> None:
    uid = message.from_user.id if message.from_user else "—"
    extra = ""
    if message.chat.type in ("group", "supergroup"):
        extra = (
            "\n\n✅ <b>Shu raqamni</b> Railway → <code>GROUP_ID</code> ga qo'ying.\n"
            "<i>Bot guruhda bo'lishi shart.</i>"
        )
    elif message.chat.type == "private" and not has_admins() and uid != "—":
        extra = f"\n\n⚙️ Railway uchun:\n<code>ADMIN_ID={uid}</code>"
    await message.answer(
        f"📌 <b>Chat ID</b>\n<code>{message.chat.id}</code>\n\n"
        f"👤 <b>Sizning ID</b>\n<code>{uid}</code>{extra}",
        parse_mode="HTML",
    )


@router.message(Command("guruh"))
async def cmd_check_group(message: Message, bot: Bot) -> None:
    """Mas'ul: GROUP_ID to‘g‘riligini tekshiradi."""
    if not can_manage_yuk(message.from_user.id if message.from_user else None):
        await message.answer("⚠️ Faqat mas'ul uchun.", parse_mode="HTML")
        return
    if message.chat.type != "private":
        await message.answer("Bu buyruqni <b>shaxsiy chatda</b> yuboring.", parse_mode="HTML")
        return
    try:
        title = await verify_group_access(bot)
        cfg = settings()["group_id"]
        resolved = get_group_id()
        fix = ""
        if resolved and cfg and resolved != cfg:
            fix = (
                f"\n\n💡 Railway da yangilang:\n"
                f"<code>GROUP_ID={resolved}</code>"
            )
        await message.answer(
            f"✅ <b>Guruh topildi</b>\n\n"
            f"📛 <b>{title}</b>\n"
            f"{parse_group_id_hint()}{fix}\n\n"
            "Endi <b>Yuk keldi</b> ishlashi kerak.",
            parse_mode="HTML",
        )
    except GroupConfigError:
        await message.answer(group_fix_message(), parse_mode="HTML")


@router.callback_query(F.data == "ui:cancel")
async def ui_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    sid = data.get("session_id")
    if sid:
        from db import cancel_draft_session

        cancel_draft_session(int(sid))
    await state.clear()
    await callback.message.edit_text(
        "❌ <b>Bekor qilindi</b>",
        parse_mode="HTML",
    )
    if can_manage_yuk(callback.from_user.id):
        active = get_active_session()
        can_finish = bool(active and active.get("status") == "active")
        await callback.message.answer(
            "Menyuga qaytdingiz.",
            reply_markup=masul_main_menu(
                can_finish=can_finish,
                show_staff=is_admin(callback.from_user.id),
            ),
        )
    await callback.answer()


def ensure_configured() -> str | None:
    if not settings()["token"]:
        return "BOT_TOKEN sozlanmagan"
    return None
