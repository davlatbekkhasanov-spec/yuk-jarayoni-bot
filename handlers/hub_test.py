"""Admin test tugmasi."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command

from hub_test import BTN_HUB_TEST, handle_admin_hub_test

router = Router(name="hub_test")


@router.message(Command("test_hub"), F.chat.type == ChatType.PRIVATE)
async def cmd_test_hub(message):
    await handle_admin_hub_test(message)


@router.message(F.text == BTN_HUB_TEST, F.chat.type == ChatType.PRIVATE)
async def btn_test_hub(message):
    await handle_admin_hub_test(message)
