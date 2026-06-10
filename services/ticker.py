"""Faol sessiya uchun live taymer yangilash."""

from __future__ import annotations

import asyncio
import logging
import os
import time

from aiogram import Bot

from config import settings
from db import get_active_session
from services.load_service import push_live_session_hub, refresh_group_status, refresh_personal_timers
from yordamchi_push import hub_configured

log = logging.getLogger(__name__)


class TimerTicker:
    def __init__(self, bot: Bot):
        self.bot = bot
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()
        self._last_hub_push = 0.0
        self._hub_push_interval = max(0, int(os.getenv("HUB_LIVE_PUSH_SEC") or "0"))

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _loop(self) -> None:
        tick = settings()["timer_tick"]
        while not self._stop.is_set():
            try:
                session = get_active_session()
                if session and session.get("status") == "active":
                    sid = int(session["id"])
                    await refresh_group_status(self.bot, sid)
                    await refresh_personal_timers(self.bot, sid)
                    if hub_configured() and self._hub_push_interval > 0:
                        now = time.monotonic()
                        if now - self._last_hub_push >= self._hub_push_interval:
                            self._last_hub_push = now
                            try:
                                await push_live_session_hub(sid)
                            except Exception as hub_err:
                                log.warning("live hub push: %s", hub_err)
            except Exception as e:
                log.exception("ticker: %s", e)
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=tick)
                break
            except asyncio.TimeoutError:
                continue
