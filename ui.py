"""Telegram HTML xabarlar va formatlash."""

from __future__ import annotations

import html as html_lib
from typing import Any

from time_util import display_now, elapsed_seconds, format_duration, now_iso
from timer_util import is_paused, pause_seconds_total, work_seconds


def he(text: object) -> str:
    return html_lib.escape(str(text or ""))


def sep() -> str:
    return "━━━━━━━━━━━━━━━━━━"


def timer_bar(seconds: int, width: int = 10) -> str:
    """Vizual «faollik» — 10 daqiqadan keyin to‘liq."""
    cap = 600
    pct = min(100, int(round(100 * min(seconds, cap) / cap)))
    filled = min(width, int(round(width * pct / 100)))
    return "▰" * filled + "▱" * (width - filled)


def status_emoji(session_status: str) -> str:
    return {
        "draft": "📝",
        "active": "🟢",
        "finishing": "🏁",
        "completed": "✅",
    }.get(session_status, "⚪")


def masul_welcome(name: str) -> str:
    return (
        f"👋 <b>Салом, {he(name)}</b>\n\n"
        f"{sep()}\n"
        "🚚 <b>Юк жараёни</b> — масъул панели\n\n"
        "📌 <b>Қадамлар:</b>\n"
        "1️⃣ <b>Юк келди</b> — машина + <b>қўшимча расм</b>\n"
        "2️⃣ Гуруҳга хабар кетади, болалар <b>Қатнашиш</b> босади\n"
        "3️⃣ Таймер + <b>⏸ Танaffus</b> / <b>▶️ Давом этиш</b>\n"
        "4️⃣ <b>Якунлаш</b> — охирги фотолар ва автоматик отчёт\n\n"
        f"<i>🕐 {he(display_now())}</i>"
    )


def photo_prompt(step: int, total: int, title: str, hint: str) -> str:
    return (
        f"📸 <b>Расм {step}/{total}</b>\n\n"
        f"<b>{he(title)}</b>\n"
        f"<i>{he(hint)}</i>\n\n"
        f"{sep()}\n"
        "⬇️ Suratni shu chatga yuboring"
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

    if phase == "finishing":
        head = "🏁 <b>ЮК ЯКУНЛАНМОҚДА</b>"
    else:
        head = "🚚 <b>ЮК КЕЛДИ</b>"

    lines = [
        head,
        "",
        f"👤 <b>Масъул:</b> {he(masul)}",
        f"🆔 <b>Сессия:</b> <code>#{sid}</code>",
        f"📊 <b>Ҳолат:</b> {status_emoji(status)} {he(status.upper())}",
        "",
        f"<b>👷 Қатнашувчилар</b> ({len(participants)})",
    ]

    if not participants:
        lines.append("<i>Ҳали hech kim qoʻshilmagan — «✅ Қатнашиш» ni bosing</i>")
    else:
        lines.append("<code>┌─────────────────────</code>")
        for i, p in enumerate(participants, 1):
            sec = work_seconds(p)
            uname = p.get("username") or ""
            at = f" @{uname}" if uname else ""
            bar = timer_bar(sec)
            if is_paused(p):
                state = "⏸ <i>танaffus</i>"
            else:
                state = "🟢"
            lines.append(
                f"<code>│</code> {i}. <b>{he(p.get('user_name'))}</b>{he(at)} {state}\n"
                f"<code>│</code>    ⏱ <b>{format_duration(sec)}</b>  <code>{bar}</code>"
            )
        lines.append("<code>└─────────────────────</code>")

    if started and phase == "active":
        total = elapsed_seconds(started)
        lines.extend(
            [
                "",
                f"⏳ <b>Жами вақт:</b> {format_duration(total)}",
            ]
        )

    lines.append(f"\n<i>🕐 {he(display_now())}</i>")
    return "\n".join(lines)


def personal_timer_card(
    *,
    session: dict[str, Any],
    participant: dict[str, Any],
) -> str:
    name = participant.get("user_name") or ""
    sec = work_seconds(participant)
    bar = timer_bar(sec)
    paused = is_paused(participant)
    pause_sum = pause_seconds_total(participant)

    if paused:
        head = "⏸ <b>Танaffus</b>"
        hint = "<i>Tаймер to‘xtatilgan. Tayyor bo‘lsangiz — «Давом этиш».</i>"
    else:
        head = "🟢 <b>Ish vaqti</b>"
        hint = "<i>Tanaffus yoki boshqa ish — «⏸ Танaffus» bosing.</i>"

    extra = ""
    if pause_sum > 0:
        extra = f"\n☕ <b>Jami tanaffus:</b> {format_duration(pause_sum)}"

    return (
        f"{head}\n\n"
        f"🚚 Юк #{session['id']}\n"
        f"👤 {he(name)}\n\n"
        f"⏱ <b>Pure ish vaqti</b>\n"
        f"<code>{bar}</code>\n"
        f"<b>{format_duration(sec)}</b>{extra}\n\n"
        f"{hint}\n\n"
        f"<i>🕐 {he(display_now())}</i>"
    )


def final_report(
    *,
    session: dict[str, Any],
    participants: list[dict[str, Any]],
) -> str:
    started = session.get("started_at") or ""
    finished = session.get("finished_at") or now_iso()
    total_sec = elapsed_seconds(started) if started else 0
    if finished and started:
        from time_util import parse_iso

        s, f = parse_iso(started), parse_iso(finished)
        if s and f:
            total_sec = max(total_sec, int((f - s).total_seconds()))

    lines = [
        "📋 <b>ЮК ЖАРАЁНИ — ОТЧЁТ</b>",
        sep(),
        "",
        f"🆔 <b>№</b> <code>#{session['id']}</code>",
        f"👤 <b>Масъул:</b> {he(session.get('masul_name'))}",
        f"🗓 <b>Сана:</b> {he(display_now())}",
        f"⏱ <b>Давомийлик:</b> {format_duration(total_sec)}",
        f"👷 <b>Қатнашувчилар:</b> {len(participants)}",
        "",
        "<b>⏱ Ҳар бир ходим</b>",
        "<code>┌────────────────────────</code>",
    ]

    if participants:
        for i, p in enumerate(participants, 1):
            sec = work_seconds(p, until_iso=finished)
            pause_sec = pause_seconds_total(p, until_iso=finished)
            tag = " ⏸" if p.get("paused_at") and finished else ""
            pause_note = f" <i>(tanaffus {format_duration(pause_sec)})</i>" if pause_sec else ""
            lines.append(
                f"<code>│</code> {i}. <b>{he(p.get('user_name'))}</b>{tag} — "
                f"⏱ {format_duration(sec)}{pause_note}"
            )
    else:
        lines.append("<code>│</code> <i>Қатнашувчи йўқ</i>")

    lines.extend(
        [
            "<code>└────────────────────────</code>",
            "",
            "📸 <b>Бошланиш:</b> машина + қўшимча расм",
            "📸 <b>Якун:</b> машина + қўшимча расм",
            "",
            sep(),
            "✅ <b>Юк жараёни тугади</b>",
        ]
    )
    return "\n".join(lines)


def operators_list_text(operators: list[dict[str, Any]]) -> str:
    lines = [
        "👥 <b>Юк масъуллари</b>",
        "<i>Юк келди / якунлаш huquqi. Railway ga qo‘shilmaydi.</i>",
        "",
    ]
    if not operators:
        lines.append("<i>Hali mas'ul yo‘q — «➕ Масъул қўшиш»</i>")
    else:
        for i, op in enumerate(operators, 1):
            lines.append(
                f"{i}. <b>{he(op.get('user_name'))}</b> — "
                f"<code>{op.get('user_id')}</code>"
            )
    lines.append(f"\n<i>🕐 {he(display_now())}</i>")
    return "\n".join(lines)


def masul_status_panel(session: dict[str, Any] | None, participants: list) -> str:
    if not session:
        return (
            "📊 <b>Ҳолат</b>\n\n"
            "<i>Ҳозирча faol yuk yo‘q.</i>\n\n"
            "🚚 Boshlash uchun <b>Юк келди</b> tugmasini bosing."
        )
    return group_load_card(session=session, participants=participants, phase="active")
