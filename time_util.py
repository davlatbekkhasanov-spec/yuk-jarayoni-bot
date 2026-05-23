"""Vaqt — Toshkent TZ."""

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from config import settings


def app_timezone() -> ZoneInfo:
    name = settings()["tz"]
    try:
        return ZoneInfo(name)
    except Exception:
        return ZoneInfo("Asia/Tashkent")


def now_dt() -> datetime:
    return datetime.now(app_timezone())


def now_iso() -> str:
    return now_dt().strftime("%Y-%m-%d %H:%M:%S")


def display_now() -> str:
    return now_dt().strftime("%d.%m.%Y · %H:%M")


def parse_iso(raw: str) -> datetime | None:
    raw = str(raw or "").strip()
    if not raw:
        return None
    tz = app_timezone()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            dt = datetime.strptime(raw, fmt)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=tz)
            return dt.astimezone(tz)
        except ValueError:
            continue
    return None


def elapsed_seconds(since_iso: str) -> int:
    start = parse_iso(since_iso)
    if not start:
        return 0
    delta = now_dt() - start
    return max(0, int(delta.total_seconds()))


def format_duration(total_sec: int) -> str:
    total_sec = max(0, int(total_sec))
    h, rem = divmod(total_sec, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h} soat {m:02d} daq"
    if m:
        return f"{m}:{s:02d}"
    return f"0:{s:02d}"
