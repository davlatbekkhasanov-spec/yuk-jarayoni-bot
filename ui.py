"""Telegram HTML — premium «вааау» ko‘rinish."""

from __future__ import annotations

import html as html_lib
from typing import Any

from time_util import display_now, elapsed_seconds, format_duration, now_iso
from timer_util import is_paused, pause_seconds_total, work_seconds

BRAND = "GLOBUS · ЮК LIVE"


def he(text: object) -> str:
    return html_lib.escape(str(text or ""))


def sep(char: str = "━", width: int = 18) -> str:
    return char * width


def banner(title: str, *, icon: str = "🚚") -> str:
    line = sep("═", 22)
    return f"{line}\n{icon} <b>{he(title)}</b>\n{line}"


def block_quote(text: str) -> str:
    return f"<blockquote>{text}</blockquote>"


def step_progress(step: int, total: int, width: int = 8) -> str:
    filled = min(width, int(round(width * step / max(total, 1))))
    return "▰" * filled + "▱" * (width - filled) + f"  <b>{step}/{total}</b>"


def timer_bar(seconds: int, width: int = 12) -> str:
    cap = 600
    pct = min(100, int(round(100 * min(seconds, cap) / cap)))
    filled = min(width, int(round(width * pct / 100)))
    return "█" * filled + "░" * (width - filled)


def percent_label(seconds: int, cap: int = 600) -> str:
    pct = min(100, int(round(100 * min(seconds, cap) / cap)))
    return f"<b>{pct}%</b>"


def rank_badge(index: int) -> str:
    if index == 1:
        return "🥇"
    if index == 2:
        return "🥈"
    if index == 3:
        return "🥉"
    return f"<code>{index:02d}</code>"


def status_chip(status: str) -> str:
    return {
        "draft": "📝 Тайёргарлик",
        "active": "🟢 LIVE",
        "finishing": "🏁 Якун",
        "completed": "✅ Тугади",
    }.get(status, "⚪")


def _team_stats(participants: list[dict[str, Any]]) -> tuple[int, int, int]:
    """active_count, paused_count, avg_work_sec."""
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
        f"👋 <b>Xush kelibsiz, {he(name)}</b>\n\n"
        f"{block_quote('⚡ Yuk jarayoni — real vaqt, professional nazorat')}\n\n"
        "🎯 <b>Tez yo‘riqnoma</b>\n"
        "┏━━━━━━━━━━━━━━━━━━━━┓\n"
        "┃ 🚚 <b>Юк келди</b> — 2 ta surat\n"
        "┃ 👷 Guruh — <b>Қатнашиш</b>\n"
        "┃ ⏸/▶️ Tanaffus — shaxsiy chat\n"
        "┃ 🏁 <b>Якунлаш</b> — avto-отчёт\n"
        "┗━━━━━━━━━━━━━━━━━━━━┛\n\n"
        f"<i>🕐 {he(display_now())}</i>"
    )


def worker_welcome() -> str:
    return (
        f"{banner('ЮК ЖАРАЁНИ', icon='👷')}\n\n"
        "Гуруҳda <b>✅ МЕН ҚАТНАШАМАН</b> bosing.\n\n"
        f"{block_quote('⏱ Shaxsiy tаймер · ⏸ tanaffus · 📊 live reyting')}\n\n"
        "<i>Mas'ul sizni avtomatik ko‘radi — zo‘r ish! 💪</i>"
    )


def photo_prompt(step: int, total: int, title: str, hint: str) -> str:
    bar = step_progress(step, total)
    return (
        f"📸 <b>SURAT YUKLASH</b>\n"
        f"<code>{bar}</code>\n\n"
        f"<b>{he(title)}</b>\n"
        f"<i>{he(hint)}</i>\n\n"
        f"{sep('─')}\n"
        "⬇️ <b>Shu yerga foto yuboring</b>"
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
        head_icon = "🏁"
        head_title = "ЮК ЯКУНЛАНМОҚДА"
    else:
        head_icon = "🚚"
        head_title = "ЮК КЕЛДИ — LIVE"

    active_n, paused_n, avg_sec = _team_stats(participants)

    lines = [
        banner(head_title, icon=head_icon),
        "",
        f"🪪 <b>Sessiya</b>  <code>#{sid}</code>",
        f"👤 <b>Mas'ul</b>  {he(masul)}",
        f"📡 <b>Holat</b>  {status_chip(status)}",
        "",
    ]

    if participants:
        sorted_p = sorted(participants, key=lambda p: work_seconds(p), reverse=True)
        lines.append(f"👷 <b>JAMOA</b>  ·  {len(participants)} kishi")
        if phase == "active":
            lines.append(
                f"<i>🟢 {active_n} ishlayapti  ·  ⏸ {paused_n} tanaffus  ·  "
                f"⌀ {format_duration(avg_sec)}</i>"
            )
        lines.append("")
        lines.append("<code>╭──────────────────────╮</code>")
        for i, p in enumerate(sorted_p, 1):
            sec = work_seconds(p)
            bar = timer_bar(sec, width=10)
            pct = percent_label(sec)
            uname = p.get("username") or ""
            at = f" @{he(uname)}" if uname else ""
            if is_paused(p):
                pulse = "⏸ <b>TANAFFUS</b>"
            else:
                pulse = "🔥 <b>FAOL</b>"
            lines.append(
                f"<code>│</code> {rank_badge(i)} <b>{he(p.get('user_name'))}</b>{at}\n"
                f"<code>│</code>    {pulse}  ⏱ <b>{format_duration(sec)}</b> {pct}\n"
                f"<code>│</code>    <code>{bar}</code>"
            )
        lines.append("<code>╰──────────────────────╯</code>")
    else:
        lines.append(
            block_quote("👇 Hozircha hech kim yo‘q — birinchi bo‘lib qatnashing!")
        )

    if started and phase == "active":
        lines.extend(["", f"⏳ <b>Yuk vaqti:</b> {format_duration(elapsed_seconds(started))}"])

    lines.extend(["", sep("─"), f"<i>🕐 {he(display_now())} · {he(BRAND)}</i>"])
    return "\n".join(lines)


def personal_timer_card(
    *,
    session: dict[str, Any],
    participant: dict[str, Any],
) -> str:
    name = participant.get("user_name") or ""
    sec = work_seconds(participant)
    bar = timer_bar(sec, width=14)
    pct = percent_label(sec)
    paused = is_paused(participant)
    pause_sum = pause_seconds_total(participant)
    sid = session["id"]

    if paused:
        mood = banner("ТАНAFFUS", icon="⏸")
        hint = "Tayyor bo‘lsangiz — <b>▶️ Давом этиш</b>"
        status_line = "💤 <i>Tаймер to‘xtatilgan</i>"
    else:
        mood = banner("ISH VAQTINGIZ", icon="🔥")
        hint = "Boshqa ishga ketdingizmi? — <b>⏸ Танaffus</b>"
        status_line = "⚡ <i>Vaqt ketyapti — zo‘r ish!</i>"

    extra = ""
    if pause_sum > 0:
        extra = f"\n☕ <b>Tanaffus jami:</b> {format_duration(pause_sum)}"

    return (
        f"{mood}\n\n"
        f"🪪 Yuk <code>#{sid}</code>  ·  👤 <b>{he(name)}</b>\n"
        f"{status_line}\n\n"
        f"⏱ <b>PURE ISH VAQTI</b>\n"
        f"<code>{bar}</code>  {pct}\n"
        f"<b>🎯 {format_duration(sec)}</b>{extra}\n\n"
        f"{block_quote(hint)}\n\n"
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
        banner("ЮК ЖАРАЁНИ — ОТЧЁТ", icon="📋"),
        "",
        f"🪪 <b>№</b> <code>#{session['id']}</code>",
        f"👤 <b>Mas'ul</b> {he(session.get('masul_name'))}",
        f"🗓 <b>Sana</b> {he(display_now())}",
        f"⏱ <b>Jami</b> {format_duration(total_sec)}",
        f"👷 <b>Jamoa</b> {len(participants)} kishi",
        "",
        "🏆 <b>REYTING — ish vaqti</b>",
        "<code>╭────────────────────────╮</code>",
    ]

    if participants:
        ranked = sorted(
            participants,
            key=lambda p: work_seconds(p, until_iso=finished),
            reverse=True,
        )
        for i, p in enumerate(ranked, 1):
            sec = work_seconds(p, until_iso=finished)
            pause_sec = pause_seconds_total(p, until_iso=finished)
            bar = timer_bar(sec, width=8)
            note = f" · ☕{format_duration(pause_sec)}" if pause_sec else ""
            lines.append(
                f"<code>│</code> {rank_badge(i)} <b>{he(p.get('user_name'))}</b>\n"
                f"<code>│</code>    ⏱ <b>{format_duration(sec)}</b>{he(note)}\n"
                f"<code>│</code>    <code>{bar}</code>"
            )
    else:
        lines.append("<code>│</code> <i>Qatnashuvchi yo‘q</i>")

    lines.extend(
        [
            "<code>╰────────────────────────╯</code>",
            "",
            "📸 <b>Galereya</b>",
            "   🚛 Машина  →  ➕ Қўшимча  →  🏁 Якун",
            "",
            sep("═", 22),
            "✨ <b>ЮК МУВАФФАҚИЯТЛИ ТУГАДИ</b> ✨",
            sep("═", 22),
        ]
    )
    return "\n".join(lines)


def operators_list_text(operators: list[dict[str, Any]]) -> str:
    lines = [
        banner("МАСЪУЛЛАР", icon="👥"),
        "<i>Юк ochish / yakunlash · Railway shart emas</i>",
        "",
    ]
    if not operators:
        lines.append(block_quote("➕ Масъул қўшиш — birinchi qadam"))
    else:
        for i, op in enumerate(operators, 1):
            lines.append(
                f"{rank_badge(i)} <b>{he(op.get('user_name'))}</b>\n"
                f"    <code>{op.get('user_id')}</code>"
            )
    lines.append(f"\n<i>🕐 {he(display_now())}</i>")
    return "\n".join(lines)


def masul_status_panel(session: dict[str, Any] | None, participants: list) -> str:
    if not session:
        return (
            f"{banner('HOLAT', icon='📊')}\n\n"
            f"{block_quote('Hozircha faol yuk yo‘q')}\n\n"
            "🚚 <b>Юк келди</b> — boshlash uchun bosing"
        )
    return group_load_card(session=session, participants=participants, phase="active")


def publish_success(session_id: int) -> str:
    return (
        f"✨ <b>YUQORI!</b> Yuk guruhga chiqdi\n\n"
        f"🪪 <code>#{session_id}</code> · {he(BRAND)}\n\n"
        "👷 Jamoa <b>Қатнашиш</b> ni bosadi\n"
        "🏁 Tayyor bo‘lgach — <b>Якунлаш</b>"
    )


def finish_success() -> str:
    return (
        f"{banner('TAYYOR!', icon='🎉')}\n\n"
        f"{block_quote('📋 Отчёт guruhga yuborildi')}\n\n"
        "Keyingi yuk → <b>🚚 Юк келди</b>"
    )


def media_caption_start(kind: str, session_id: int) -> str:
    labels = {
        "car": ("🚛", "МАШИНА", "бошланиш"),
        "extra": ("➕", "ҚЎШИМАЧА", "бошланиш"),
    }
    icon, title, phase = labels.get(kind, ("📷", "SURAT", ""))
    return (
        f"{icon} <b>{title}</b>\n"
        f"<i>{he(phase)}</i>\n"
        f"{sep('─')}\n"
        f"🪪 #{session_id} · <b>LIVE</b>"
    )


def media_caption_end(kind: str) -> str:
    labels = {
        "car": ("🚛", "МАШИНА", "якун"),
        "extra": ("➕", "ҚЎШИМАЧА", "якун"),
    }
    icon, title, phase = labels.get(kind, ("📷", "SURAT", ""))
    return f"{icon} <b>{title}</b> · <i>{he(phase)}</i>"
