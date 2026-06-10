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
from services.load_service import backfill_hub_summaries
from states import AddOperatorStates
from texts import BTN_MASUL_QOSH_ALL, BTN_MASULLAR_ALL
from ui import operators_list_text
from yordamchi_push import hub_configured, today_iso

router = Router()


def _menu(uid: int):
    active = get_active_session()
    return masul_main_menu(
        can_finish=bool(active and active.get("status") == "active"),
        show_staff=is_admin(uid),
    )


@router.message(F.text.in_(BTN_MASULLAR_ALL), F.chat.type == "private")
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


@router.message(F.text.in_(BTN_MASUL_QOSH_ALL), F.chat.type == "private")
async def add_op_start(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("⚠️ Faqat asosiy admin uchun.", parse_mode="HTML")
        return
    await state.set_state(AddOperatorStates.waiting)
    await message.answer(
        "➕ <b>Mas'ul qo'shish</b>\n\n"
        "1) Odamning xabarini <b>reply</b> qiling, yoki\n"
        "2) <code>123456789</code> — Telegram ID yozing, yoki\n"
        "3) Kontaktni <b>forward</b> qiling.\n\n"
        "<i>Ularga «Yuk keldi» va «Yakunlash» ochiladi.</i>\n\n"
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
        "Endi u botda <b>Yuk keldi</b> va <b>Yakunlash</b> bosishi mumkin.",
        parse_mode="HTML",
        reply_markup=_menu(message.from_user.id),
    )


@router.message(F.text.regexp(r"^/hubbackfill(?:@\w+)?(?:\s+(\d{4}-\d{2}-\d{2}))?\s*$"), F.chat.type == "private")
async def hub_backfill_cmd(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("⚠️ Faqat asosiy admin uchun.", parse_mode="HTML")
        return
    if not hub_configured():
        await message.answer(
            "⚠️ Hub sozlanmagan.\n"
            "Railway: <code>YORDAMCHI_HUB_URL</code> + <code>YORDAMCHI_HUB_SECRET</code>",
            parse_mode="HTML",
        )
        return
    m = re.search(r"(\d{4}-\d{2}-\d{2})", message.text or "")
    day = m.group(1) if m else today_iso()
    sent, total = await backfill_hub_summaries(day)
    await message.answer(
        f"📡 <b>Hub backfill</b> — <code>{day}</code>\n"
        f"Yuborildi: <b>{sent}</b> / {total} xodim\n\n"
        "<i>Yordamchi botda /repairhub bosing.</i>",
        parse_mode="HTML",
        reply_markup=_menu(message.from_user.id),
    )
