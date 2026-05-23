"""Юк жараёни — Telegram bot."""

from __future__ import annotations

import asyncio
import logging
import sys

from dotenv import load_dotenv

load_dotenv()

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import settings, startup_warnings
from db import init_db
from handlers import setup_routers
from handlers.common import ensure_configured
from services.ticker import TimerTicker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger(__name__)


async def main() -> None:
    err = ensure_configured()
    if err:
        log.error("%s", err)
        sys.exit(1)

    for warn in startup_warnings():
        log.warning(warn)

    init_db()
    cfg = settings()
    bot = Bot(
        token=cfg["token"],
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(setup_routers())

    ticker = TimerTicker(bot)
    await ticker.start()
    log.info("Bot ishga tushdi (GROUP_ID=%s)", cfg["group_id"])

    try:
        await dp.start_polling(bot)
    finally:
        await ticker.stop()


if __name__ == "__main__":
    asyncio.run(main())
