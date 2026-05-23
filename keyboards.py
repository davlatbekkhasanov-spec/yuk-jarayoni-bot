"""Reply va Inline tugmalar — lotin."""

from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from callbacks import FinishCb, JoinCb, PauseCb
from texts import (
    BTN_HOLAT,
    BTN_MASUL_QOSH,
    BTN_MASULLAR,
    BTN_YAKUNLASH,
    BTN_YUK_KELDI,
    INL_BEKOR,
    INL_DAVOM,
    INL_HA_YAKUN,
    INL_ORQAGA,
    INL_QATNASH,
    INL_TANAFFUS,
    INL_YAKUNLANDI,
)


def masul_main_menu(*, can_finish: bool, show_staff: bool = False) -> ReplyKeyboardMarkup:
    row2 = [KeyboardButton(text=BTN_HOLAT)]
    if can_finish:
        row2.append(KeyboardButton(text=BTN_YAKUNLASH))
    keyboard = [
        [KeyboardButton(text=BTN_YUK_KELDI)],
        row2,
    ]
    if show_staff:
        keyboard.append(
            [
                KeyboardButton(text=BTN_MASULLAR),
                KeyboardButton(text=BTN_MASUL_QOSH),
            ]
        )
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder="Menyudan tanlang...",
    )


def cancel_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=INL_BEKOR, callback_data="ui:cancel")]
        ]
    )


def group_join_keyboard(session_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=INL_QATNASH,
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
                    text=INL_YAKUNLANDI,
                    callback_data=JoinCb(session_id=session_id, closed=1).pack(),
                )
            ]
        ]
    )


def personal_timer_keyboard(session_id: int, *, paused: bool) -> InlineKeyboardMarkup:
    if paused:
        btn = InlineKeyboardButton(
            text=INL_DAVOM,
            callback_data=PauseCb(session_id=session_id, action="resume").pack(),
        )
    else:
        btn = InlineKeyboardButton(
            text=INL_TANAFFUS,
            callback_data=PauseCb(session_id=session_id, action="pause").pack(),
        )
    return InlineKeyboardMarkup(inline_keyboard=[[btn]])


def masul_finish_confirm(session_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=INL_HA_YAKUN,
                    callback_data=FinishCb(session_id=session_id, confirm=1).pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text=INL_ORQAGA,
                    callback_data=FinishCb(session_id=session_id, confirm=0).pack(),
                ),
            ],
        ]
    )
