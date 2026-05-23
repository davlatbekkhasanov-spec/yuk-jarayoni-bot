"""Reply va Inline tugmalar."""

from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from callbacks import JoinCb, FinishCb


def masul_main_menu(*, can_finish: bool) -> ReplyKeyboardMarkup:
    row2 = [KeyboardButton(text="📊 Ҳолат")]
    if can_finish:
        row2.append(KeyboardButton(text="🏁 Якунлаш"))
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🚚 Юк келди")],
            row2,
        ],
        resize_keyboard=True,
        input_field_placeholder="Menyudan tanlang…",
    )


def cancel_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Бекор қилиш", callback_data="ui:cancel")]
        ]
    )


def group_join_keyboard(session_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Қатнашиш",
                    callback_data=JoinCb(session_id=session_id).pack(),
                )
            ]
        ]
    )


def group_join_closed(session_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔒 Якунланди",
                    callback_data=JoinCb(session_id=session_id, closed=1).pack(),
                )
            ]
        ]
    )


def masul_finish_confirm(session_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Ҳа, якунлаш",
                    callback_data=FinishCb(session_id=session_id, confirm=1).pack(),
                ),
                InlineKeyboardButton(
                    text="↩️ Орқага",
                    callback_data=FinishCb(session_id=session_id, confirm=0).pack(),
                ),
            ]
        ]
    )
