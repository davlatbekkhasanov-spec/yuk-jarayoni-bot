"""Kaizen metrikalari — faqat vaqt (foiz/ball keyinroq qo'shiladi)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from time_util import elapsed_seconds, parse_iso
from timer_util import pause_seconds_total, work_seconds


@dataclass
class KaizenMetrics:
    cycle_sec: int
    total_work_sec: int
    total_pause_sec: int
    headcount: int
    avg_work_sec: int
    fastest_name: str
    fastest_sec: int
    slowest_name: str
    slowest_sec: int


def compute_kaizen(
    *,
    session: dict[str, Any],
    participants: list[dict[str, Any]],
    finished_iso: str,
) -> KaizenMetrics:
    started = session.get("started_at") or ""
    cycle = 0
    if started and finished_iso:
        s, f = parse_iso(started), parse_iso(finished_iso)
        if s and f:
            cycle = max(0, int((f - s).total_seconds()))
    if cycle <= 0 and started:
        cycle = elapsed_seconds(started)

    work_list: list[tuple[str, int]] = []
    total_pause = 0
    for p in participants:
        w = work_seconds(p, until_iso=finished_iso)
        work_list.append((str(p.get("user_name") or "?"), w))
        total_pause += pause_seconds_total(p, until_iso=finished_iso)

    total_work = sum(w for _, w in work_list)
    n = len(work_list)
    avg = int(total_work / n) if n else 0

    if work_list:
        fastest_name, fastest_sec = min(work_list, key=lambda x: x[1])
        slowest_name, slowest_sec = max(work_list, key=lambda x: x[1])
    else:
        fastest_name, fastest_sec = "—", 0
        slowest_name, slowest_sec = "—", 0

    return KaizenMetrics(
        cycle_sec=cycle,
        total_work_sec=total_work,
        total_pause_sec=total_pause,
        headcount=n,
        avg_work_sec=avg,
        fastest_name=fastest_name,
        fastest_sec=fastest_sec,
        slowest_name=slowest_name,
        slowest_sec=slowest_sec,
    )


def avg_minutes(sec: int) -> str:
    if sec < 60:
        return f"{sec} soniya"
    m = sec // 60
    s = sec % 60
    if s:
        return f"{m} daq {s} son"
    return f"{m} daqiqa"
