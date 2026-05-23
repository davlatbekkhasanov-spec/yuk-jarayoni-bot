"""Admin: mas'ullarni bot ichida qo'shish (Railway shart emas)."""

from __future__ import annotations

import re

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import is_admin
from db import add_operator, get_active_session, list_operators, remove_operator
from keyboards import masul_main_menu
from roles import can_manage_yuk
from states import AddOperatorStates
from ui import operators_list_text

router = Router()


def _menu(uid: int):
    active = get_active_session()
    return masul_main_menu(
        can_finish=bool(active and active.get("status") == "active"),
        show_staff=is_admin(uid),
    )


@router.message(F.text == "👥 Масъуллар", F.chat.type == "private")
async def list_ops(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("⚠️ Faqat asosiy admin uchun.", parse_mode="HTML")
        return
    ops = list_operators()
    await message.answer(
        operators_list_text(ops),
        parse_mode="HTML",
        reply_markup=_menu(message.from_user.id),
    )


@router.message(F.text == "➕ Масъул қўшиш", F.chat.type == "private")
async def add_op_start(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("⚠️ Faqat asosiy admin uchun.", parse_mode="HTML")
        return
    await state.set_state(AddOperatorStates.waiting)
    await message.answer(
        "➕ <b>Масъул қўшиш</b>\n\n"
        "1) Odamning xabarini <b>reply</b> qiling, yoki\n"
        "2) <code>123456789</code> — Telegram ID yozing, yoki\n"
        "3) Kontaktni <b>forward</b> qiling.\n\n"
        "<i>Ularga «Юк келди» va «Якунлаш» ochiladi.</i>\n\n"
        "💡 Doimiy saqlash: Railway → <code>MASUL_IDS=id1,id2</code> "
        "(har deployda qayta tiklanadi).",
        parse_mode="HTML",
    )


@router.message(AddOperatorStates.waiting, F.chat.type == "private")
async def add_op_save(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await state.clear()
        return

    target_id: int | None = None
    target_name = ""

    if message.forward_from:
        target_id = message.forward_from.id
        target_name = message.forward_from.full_name or ""
    elif message.reply_to_message and message.reply_to_message.from_user:
        target_id = message.reply_to_message.from_user.id
        target_name = message.reply_to_message.from_user.full_name or ""
    elif message.contact and message.contact.user_id:
        target_id = message.contact.user_id
        target_name = message.contact.first_name or ""
    else:
        m = re.search(r"-?\d{6,}", message.text or "")
        if m:
            target_id = int(m.group())

    if not target_id:
        await message.answer(
            "⚠️ ID topilmadi. Reply, forward yoki raqam yuboring.",
            parse_mode="HTML",
        )
        return

    if is_admin(target_id):
        await message.answer(
            "ℹ️ Bu kishi allaqachon asosiy <b>admin</b> (Railway).",
            parse_mode="HTML",
        )
        await state.clear()
        return

    name = target_name or f"ID {target_id}"
    add_operator(
        user_id=target_id,
        user_name=name,
        added_by=message.from_user.id,
    )
    await state.clear()
    await message.answer(
        f"✅ <b>{name}</b> mas'ul qilindi.\n"
        f"<code>{target_id}</code>\n\n"
        "Endi u botda <b>🚚 Юк келди</b> va <b>🏁 Якунлаш</b> bosa oladi.",
        parse_mode="HTML",
        reply_markup=_menu(message.from_user.id),
    )
