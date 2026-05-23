"""Telegram HTML — premium + Kaizen."""

from __future__ import annotations

import html as html_lib
from typing import Any

from kaizen import KaizenMetrics, avg_minutes, compute_kaizen
from texts import BRAND, INL_DAVOM, INL_QATNASH, INL_TANAFFUS
from time_util import display_now, elapsed_seconds, format_duration, now_iso
from timer_util import is_paused, pause_seconds_total, work_seconds

_live_pulse_i = 0


def live_pulse() -> str:
    """Miltillovchi LIVE nuqta (har yangilanishda almashadi)."""
    global _live_pulse_i
    _live_pulse_i += 1
    return "🔴" if _live_pulse_i % 2 else "⚫"


def he(text: object) -> str:
    return html_lib.escape(str(text or ""))


def sep(char: str = "─", width: int = 24) -> str:
    return char * width


def banner(title: str, *, icon: str = "🚚", width: int = 24) -> str:
    line = sep("═", width)
    return f"{line}\n{icon}  <b>{he(title)}</b>\n{line}"


def glow_bar(pct: int, width: int = 14) -> str:
    pct = max(0, min(100, int(pct)))
    filled = min(width, int(round(width * pct / 100)))
    return "▰" * filled + "▱" * (width - filled)


def timer_bar(seconds: int, width: int = 12) -> str:
    return glow_bar(min(100, int(round(100 * min(seconds, 600) / 600))), width)


def step_progress(step: int, total: int, width: int = 10) -> str:
    pct = int(round(100 * step / max(total, 1)))
    return f"{glow_bar(pct, width)}  <b>{step}/{total}</b>"


def rank_badge(index: int) -> str:
    if index == 1:
        return "🥇"
    if index == 2:
        return "🥈"
    if index == 3:
        return "🥉"
    return f"#{index:02d}"


def status_chip(status: str) -> str:
    return {
        "draft": "📝 Tayyor",
        "active": "🟢 LIVE",
        "finishing": "🏁 Yakun",
        "completed": "✅ OK",
    }.get(status, "⚪")


def metric_card(icon: str, title: str, value: str, *, bar_pct: int | None = None) -> str:
    lines = [f"{icon}  <b>{he(title)}</b>", f"    <code>{he(value)}</code>"]
    if bar_pct is not None:
        lines.append(f"    <code>{glow_bar(bar_pct, 12)}</code>  <b>{bar_pct}%</b>")
    return "\n".join(lines)


def _team_stats(participants: list[dict[str, Any]]) -> tuple[int, int, int]:
    if not participants:
        return 0, 0, 0
    active = sum(1 for p in participants if not is_paused(p))
    paused = len(participants) - active
    times = [work_seconds(p) for p in participants]
    avg = int(sum(times) / len(times)) if times else 0
    return active, paused, avg


def masul_welcome(name: str) -> str:
    return (
        f"{banner(BRAND, icon='✨')}\n\n"
        f"👋  <b>Xush kelibsiz, {he(name)}</b>\n\n"
        "┏━━━━━━━━━━━━━━━━━━━━━━┓\n"
        "┃  🚚  Yuk keldi\n"
        f"┃  👷  {INL_QATNASH}\n"
        "┃  ⏸   Tanaffus / Davom\n"
        "┃  🏁  Yakun + Kaizen\n"
        "┗━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
        f"<i>🕐 {he(display_now())}</i>"
    )


def worker_welcome() -> str:
    return (
        f"{banner('YUK JARAYONI', icon='👷')}\n\n"
        f"🔽  <b>{INL_QATNASH}</b>\n\n"
        "<i>⏱ Taymer  ·  ⏸ Tanaffus  ·  🏆 Reyting</i>"
    )


def photo_prompt(step: int, total: int, title: str, hint: str) -> str:
    return (
        f"📸  <b>SURAT {step}/{total}</b>\n"
        f"<code>{step_progress(step, total)}</code>\n\n"
        f"<b>{he(title)}</b>\n"
        f"<i>{he(hint)}</i>\n\n"
        "⬇️  <b>Fotoni yuboring</b>"
    )


def group_load_card(
    *,
    session: dict[str, Any],
    participants: list[dict[str, Any]],
    phase: str = "active",
) -> str:
    sid = session["id"]
    masul = session.get("masul_name") or "—"
    status = session.get("status") or "active"
    started = session.get("started_at") or ""

    if phase in ("finishing", "completed"):
        head_icon, head_title = "✅", "JARAYON YAKUNLANDI"
    else:
        head_icon, head_title = live_pulse(), "YUK KELDI"

    active_n, paused_n, avg_sec = _team_stats(participants)
    cycle = elapsed_seconds(started) if started else 0
    finished_iso = session.get("finished_at") or now_iso()
    until = finished_iso if phase in ("finishing", "completed") else None

    lines = [
        banner(head_title, icon=head_icon),
        "",
        f"🪪  Sessiya   <code>#{sid}</code>",
        f"👤  Mas'ul   <b>{he(masul)}</b>",
        f"📡  Holat    {status_chip(status)}",
        "",
    ]

    if participants:
        sort_key = (
            (lambda p: work_seconds(p, until_iso=until))
            if until
            else work_seconds
        )
        sorted_p = sorted(participants, key=sort_key, reverse=True)
        lines.append(f"👷  <b>JAMOA</b>   {len(participants)} kishi")
        if phase == "active":
            lines.append(
                f"<i>🟢 {active_n} faol  ·  ⏸ {paused_n} pauza  ·  "
                f"⌀ {format_duration(avg_sec)}</i>"
            )
        lines.append("")
        lines.append("<code>╭────────────────────────╮</code>")
        for i, p in enumerate(sorted_p, 1):
            sec = work_seconds(p, until_iso=until) if until else work_seconds(p)
            if is_paused(p):
                pulse, st = "⏸", "PAUZA"
            else:
                pulse, st = "🔥", "FAOL"
            lines.append(
                f"<code>│</code> {rank_badge(i)}  <b>{he(p.get('user_name'))}</b>  "
                f"<i>{st}</i>\n"
                f"<code>│</code>     {pulse}  ⏱  <b>{format_duration(sec)}</b>\n"
                f"<code>│</code>     <code>{timer_bar(sec, 11)}</code>"
            )
        lines.append("<code>╰────────────────────────╯</code>")
    else:
        lines.extend(
            [
                sep("·"),
                "⚡  <b>Hozircha jamoa yo'q</b>",
                f"🔽  Birinchi bo'ling — <b>{INL_QATNASH}</b>",
                sep("·"),
            ]
        )

    if started and phase == "active":
        lines.extend(
            [
                "",
                f"⏳  <b>Yuk vaqti</b>  {format_duration(cycle)}",
                f"<code>{glow_bar(min(100, cycle // 6), 16)}</code>",
            ]
        )

    if phase == "completed":
        m = compute_kaizen(
            session=session,
            participants=participants,
            finished_iso=finished_iso,
        )
        lines.extend(["", kaizen_summary_compact(m)])

    pulse = live_pulse()
    if phase in ("finishing", "completed"):
        footer_live = ""
    else:
        footer_live = f"  ·  {pulse} <b>LIVE</b>"
    lines.extend(
        ["", sep(), f"<i>🕐 {he(display_now())}{footer_live}  ·  {he(BRAND)}</i>"]
    )
    return "\n".join(lines)


def personal_timer_card(
    *,
    session: dict[str, Any],
    participant: dict[str, Any],
) -> str:
    name = participant.get("user_name") or ""
    sec = work_seconds(participant)
    paused = is_paused(participant)
    pause_sum = pause_seconds_total(participant)
    sid = session["id"]

    if paused:
        head = banner("TANAFFUS", icon="⏸")
        hint = f"▶️  {INL_DAVOM}"
        sub = "💤  Taymer to'xtatilgan"
    else:
        head = banner("ISH VAQTI", icon="🔥")
        hint = f"⏸  {INL_TANAFFUS}"
        sub = "⚡  Zo'r tempo!"

    extra = f"\n☕  Tanaffus: <b>{format_duration(pause_sum)}</b>" if pause_sum else ""

    return (
        f"{head}\n\n"
        f"🪪  #{sid}  ·  👤  <b>{he(name)}</b>\n"
        f"<i>{sub}</i>\n\n"
        f"⏱  <b>{format_duration(sec)}</b>\n"
        f"<code>{timer_bar(sec, 16)}</code>{extra}\n\n"
        f"<i>{hint}</i>\n\n"
        f"<i>🕐 {he(display_now())}</i>"
    )


def kaizen_summary_compact(m: KaizenMetrics) -> str:
    """Status kartasida ko'rinadigan qisqa Kaizen (faqat vaqt)."""
    return (
        f"{sep()}\n"
        f"📊  <b>KAIZEN</b>\n"
        f"⏱  Jami tushirish: <b>{format_duration(m.cycle_sec)}</b>\n"
        f"👤  O'rtacha / xodim: <b>{avg_minutes(m.avg_work_sec)}</b>\n"
        f"👷  Jamoa ish vaqti: <b>{format_duration(m.total_work_sec)}</b>\n"
        f"☕  Tanaffus: <b>{format_duration(m.total_pause_sec)}</b>"
    )


def kaizen_block(m: KaizenMetrics) -> str:
    return (
        f"{banner('KAIZEN  ·  YAKUNIY TAHLIL', icon='📊', width=26)}\n\n"
        f"{metric_card('⏱', 'Jami tushirish vaqti', format_duration(m.cycle_sec))}\n\n"
        f"{metric_card('👤', 'Bir xodim o\'rtacha', avg_minutes(m.avg_work_sec))}\n\n"
        f"{metric_card('👷', 'Jamoa jami ish vaqti', format_duration(m.total_work_sec))}\n\n"
        f"{metric_card('☕', 'Tanaffus', format_duration(m.total_pause_sec))}\n\n"
        f"🏅  <b>Eng tez:</b> {he(m.fastest_name)} — {format_duration(m.fastest_sec)}\n"
        f"🐢  <b>Eng sekin:</b> {he(m.slowest_name)} — {format_duration(m.slowest_sec)}"
    )


def ranking_block(
    participants: list[dict[str, Any]], *, finished_iso: str
) -> str:
    lines = [
        "🏆  <b>REYTING</b>",
        "<code>╭────────────────────────╮</code>",
    ]
    if not participants:
        lines.append("<code>│</code>  <i>Ishtirokchi yo'q</i>")
    else:
        ranked = sorted(
            participants,
            key=lambda p: work_seconds(p, until_iso=finished_iso),
            reverse=True,
        )
        for i, p in enumerate(ranked, 1):
            sec = work_seconds(p, until_iso=finished_iso)
            lines.append(
                f"<code>│</code> {rank_badge(i)}  <b>{he(p.get('user_name'))}</b>\n"
                f"<code>│</code>      ⏱  {format_duration(sec)}  "
                f"<code>{timer_bar(sec, 8)}</code>"
            )
    lines.append("<code>╰────────────────────────╯</code>")
    return "\n".join(lines)


def final_report(
    *,
    session: dict[str, Any],
    participants: list[dict[str, Any]],
) -> str:
    finished = session.get("finished_at") or now_iso()
    m = compute_kaizen(session=session, participants=participants, finished_iso=finished)

    return (
        f"{banner('HISOBOT', icon='📋')}\n\n"
        f"🪪  <code>#{session['id']}</code>  ·  👤  <b>{he(session.get('masul_name'))}</b>\n"
        f"🗓  {he(display_now())}  ·  👷  {m.headcount} kishi\n\n"
        f"{ranking_block(participants, finished_iso=finished)}\n\n"
        f"{kaizen_block(m)}\n\n"
        "📸  🚛 Mashina  →  ➕ Qo'shimcha  →  🏁 Yakun\n\n"
        f"✨  <b>YUK MUVAFFAQIYATLI TUGADI</b>  ✨"
    )


def report_caption_short(session: dict[str, Any], participants: list) -> str:
    finished = session.get("finished_at") or now_iso()
    m = compute_kaizen(
        session=session, participants=participants, finished_iso=finished
    )
    return (
        f"🏁  <b>YAKUN SURATLARI</b>  ·  #{session['id']}\n"
        f"{sep()}\n"
        f"⏱  Jami: <b>{format_duration(m.cycle_sec)}</b>  ·  "
        f"👤  O'rtacha: <b>{avg_minutes(m.avg_work_sec)}</b>"
    )


def operators_list_text(operators: list[dict[str, Any]]) -> str:
    lines = [banner("MAS'ULLAR", icon="👥"), ""]
    if not operators:
        lines.append("<i>➕ Mas'ul qo'shish</i>")
    else:
        for i, op in enumerate(operators, 1):
            lines.append(
                f"{rank_badge(i)}  <b>{he(op.get('user_name'))}</b>\n"
                f"    <code>{op.get('user_id')}</code>"
            )
    lines.append(f"\n<i>🕐 {he(display_now())}</i>")
    return "\n".join(lines)


def masul_status_panel(session: dict[str, Any] | None, participants: list) -> str:
    if not session:
        return (
            f"{banner('HOLAT', icon='📊')}\n\n"
            "<i>Faol yuk yo'q</i>\n\n"
            "🚚  <b>Yuk keldi</b> ni bosing"
        )
    return group_load_card(session=session, participants=participants, phase="active")


def publish_success(session_id: int) -> str:
    return (
        f"✨  <b>LIVE!</b>  Yuk #{session_id}\n\n"
        f"👷  {INL_QATNASH}\n"
        "🏁  Keyin <b>Yakunlash</b>"
    )


def finish_success() -> str:
    return (
        f"{banner('TAYYOR', icon='🎉')}\n\n"
        "📊  <b>Kaizen hisobot</b> guruhga yuborildi"
    )


def media_caption_start(kind: str, session_id: int) -> str:
    labels = {
        "car": ("🚛", "MASHINA"),
        "extra": ("➕", "QO'SHIMCHA"),
    }
    icon, title = labels.get(kind, ("📷", "SURAT"))
    return f"{icon}  <b>{title}</b>  ·  boshlanish\n🪪  #{session_id}"


def media_caption_end(kind: str) -> str:
    labels = {"car": ("🚛", "MASHINA"), "extra": ("➕", "QO'SHIMCHA")}
    icon, title = labels.get(kind, ("📷", "SURAT"))
    return f"{icon}  <b>{title}</b>  ·  yakun"
