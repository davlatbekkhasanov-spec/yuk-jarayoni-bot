"""Jonli hub sessiyalarini yuk DB holati bilan moslashtirish."""

from __future__ import annotations

import json
import logging
import urllib.request

from db import get_active_session, get_session, list_participants
from yordamchi_push import HUB_SECRET, HUB_URL, push_session_end_background

log = logging.getLogger(__name__)


def reconcile_hub_live_sessions() -> None:
    """DB da faol yuk yo'q bo'lsa — hub dagi yuk sessiyalarini yopish."""
    active = get_active_session()
    allowed: set[int] = set()
    if active and active.get("status") in ("active", "finishing"):
        sid = int(active["id"])
        sess = get_session(sid) or active
        masul_id = int(sess.get("masul_id") or 0)
        if masul_id:
            allowed.add(masul_id)
        for p in list_participants(sid):
            uid = int(p.get("user_id") or 0)
            if uid:
                allowed.add(uid)

    if not HUB_URL or not HUB_SECRET:
        return
    try:
        req = urllib.request.Request(
            f"{HUB_URL.rstrip('/')}/api/live",
            headers={"Accept": "application/json"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        for sess in data.get("sessions") or []:
            if str(sess.get("bot_key") or "") != "yuk":
                continue
            uid = int(sess.get("tg_id") or 0)
            if uid and uid not in allowed:
                push_session_end_background(tg_id=uid, bot_key="yuk", activity_type="yuk")
                log.info("Hub live reconcile: yuk sessiya yopildi tg=%s", uid)
    except Exception as e:
        log.debug("yuk hub reconcile: %s", e)


def abandon_stuck_active_yuk(*, max_age_hours: float = 6.0) -> bool:
    """Juda uzoq davom etgan qotib qolgan yukni yopish."""
    import os

    from time_util import now_iso, parse_iso

    from db import abandon_session
    from services.load_service import push_live_session_end

    active = get_active_session()
    if not active or active.get("status") != "active":
        return False
    if os.getenv("YUK_FORCE_ABANDON_ACTIVE", "").strip().lower() in ("1", "true", "yes"):
        sid = int(active["id"])
        push_live_session_end(sid)
        abandon_session(sid)
        log.warning("YUK_FORCE_ABANDON_ACTIVE: yuk #%s bekor qilindi", sid)
        return True
    started = str(active.get("started_at") or active.get("created_at") or "")
    if not started:
        return False
    try:
        age_h = (parse_iso(now_iso()) - parse_iso(started)).total_seconds() / 3600.0
    except (TypeError, ValueError):
        return False
    if age_h < max_age_hours:
        return False
    sid = int(active["id"])
    push_live_session_end(sid)
    abandon_session(sid)
    log.warning("Qotib qolgan yuk #%s bekor qilindi (%.1f soat)", sid, age_h)
    return True
