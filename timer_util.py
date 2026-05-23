"""Ish vaqti — tanaffus/pauza hisobga olinadi."""

from __future__ import annotations

from typing import Any

from time_util import elapsed_seconds, now_dt, parse_iso


def is_paused(participant: dict[str, Any]) -> bool:
    return bool(participant.get("paused_at"))


def pause_seconds_total(participant: dict[str, Any], *, until_iso: str | None = None) -> int:
    total = int(participant.get("pause_total_sec") or 0)
    paused_at = participant.get("paused_at")
    if not paused_at:
        return total
    if until_iso:
        start = parse_iso(paused_at)
        end = parse_iso(until_iso)
        if start and end and end > start:
            total += int((end - start).total_seconds())
        return total
    total += elapsed_seconds(paused_at)
    return total


def work_seconds(participant: dict[str, Any], *, until_iso: str | None = None) -> int:
    joined = participant.get("joined_at") or ""
    if until_iso:
        start = parse_iso(joined)
        end = parse_iso(until_iso) or now_dt()
        if not start:
            return 0
        gross = max(0, int((end - start).total_seconds()))
    else:
        gross = elapsed_seconds(joined)
    paused = pause_seconds_total(participant, until_iso=until_iso)
    return max(0, gross - paused)
