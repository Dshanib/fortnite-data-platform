"""Format QueryService responses for Telegram (Hebrew UI, HTML)."""

from __future__ import annotations

from typing import Any, Callable, Dict, List

from common.models import QueryResponse

from bot import copy_he as t
from bot.ui import (
    back_menu_keyboard,
    esc,
    format_number,
    format_timestamp,
    main_menu_keyboard,
    screen_header,
)


def welcome_text() -> str:
    return (
        f"<b>🎮 {esc(t.WELCOME_TITLE)}</b>\n"
        f"<i>{esc(t.WELCOME_TAGLINE)}</i>\n\n"
        f"{t.WELCOME_BODY}"
    )


def help_text() -> str:
    return (
        f"<b>{esc(t.HELP_TITLE)}</b>\n"
        f"{t.HELP_BODY}"
    )


def unknown_input_text() -> str:
    return esc(t.UNKNOWN_INPUT)


def _format_pct_change(value: Any) -> str:
    if value is None:
        return "—"
    try:
        return f"{format_number(float(value) * 100.0, decimals=0)}%"
    except (TypeError, ValueError):
        return "—"


def _status_screen(title: str, detail: str, *, hint: str) -> str:
    return (
        f"{screen_header(title, detail)}\n"
        f"<i>{esc(hint)}</i>"
    )


def format_no_data(response: QueryResponse) -> str:
    detail = response.message or t.NO_DATA_HINT
    return _status_screen(t.NO_DATA_TITLE, detail, hint="")


def format_error(response: QueryResponse) -> str:
    detail = response.message or t.ERROR_HINT
    return _status_screen(t.ERROR_TITLE, detail, hint=t.ERROR_HINT)


def _rarity_label(raw: Any) -> str:
    key = str(raw or "unknown").strip().lower()
    return t.RARITY_LABELS.get(key, esc(raw))


def _status_label(raw: Any) -> str:
    key = str(raw or "").strip().lower()
    return t.STATUS_LABELS.get(key, esc(raw))


def format_current_activity(response: QueryResponse) -> str:
    if response.status == "no_data":
        return format_no_data(response)
    if response.status == "error":
        return format_error(response)

    row = (response.data or [{}])[0]
    title = row.get("title") or t.UNKNOWN_ISLAND
    code = row.get("island_code", "?")
    peak = format_number(row.get("peak_ccu"))
    total = format_number(row.get("total_peak_ccu"))
    updated = format_timestamp(
        row.get("data_as_of") or row.get("latest_metric_timestamp")
    )

    body = (
        f"🥇 <b>{esc(t.LABEL_ISLAND)}:</b> {esc(title)}\n"
        f"🔑 <b>{esc(t.LABEL_CODE)}:</b> <code>{esc(code)}</code>\n\n"
        f"👥 <b>{esc(t.LABEL_PEAK_CCU)}:</b> {peak}\n"
        f"📊 <b>{esc(t.LABEL_TOTAL_CCU)}:</b> {total}\n\n"
        f"🕐 <b>{esc(t.LABEL_UPDATED)}:</b> {updated}"
    )
    return f"{screen_header(t.TITLE_ACTIVITY, t.TITLE_ACTIVITY_SUB)}\n{body}"


def format_top_islands(response: QueryResponse) -> str:
    if response.status == "no_data":
        return format_no_data(response)
    if response.status == "error":
        return format_error(response)

    rows = response.data or []
    lines = [screen_header(t.TITLE_TOP_ISLANDS, t.TITLE_TOP_ISLANDS_SUB)]
    if not rows:
        lines.append(f"\n<i>{esc(t.NO_DATA_HINT)}</i>")
        return "\n".join(lines)

    if len(rows) <= 2:
        lines.append(f"\n<i>{esc(t.TOP_ISLANDS_FEW)}</i>")

    for row in rows[:10]:
        rank = row.get("rank", "?")
        title = row.get("title") or row.get("island_code") or t.UNKNOWN_ISLAND
        peak = format_number(row.get("peak_ccu"))
        players = format_number(row.get("unique_players"))
        lines.append(
            f"\n<b>#{esc(rank)}</b> {esc(title)}\n"
            f"   {esc(t.LABEL_PEAK_CCU)}: {peak} · {esc(t.LABEL_PLAYERS)}: {players}"
        )
    return "\n".join(lines)


def format_shop_summary(response: QueryResponse) -> str:
    if response.status == "no_data":
        return format_no_data(response)
    if response.status == "error":
        return format_error(response)

    snap = "—"
    updated = "—"
    lines = [screen_header(t.TITLE_SHOP, t.TITLE_SHOP_SUB)]
    for row in response.data or []:
        rarity = _rarity_label(row.get("rarity"))
        count = format_number(row.get("item_count"))
        share = format_number(row.get("share_pct"), decimals=1)
        snap = format_timestamp(row.get("snapshot_date")) if row.get("snapshot_date") else snap
        if row.get("updated_at"):
            updated = format_timestamp(row.get("updated_at"))
        lines.append(f"\n• <b>{rarity}</b> — {count} פריטים ({share}%)")

    lines.append(f"\n📅 <b>{esc(t.LABEL_SNAPSHOT)}:</b> {snap}")
    lines.append(f"🕐 <b>{esc(t.LABEL_UPDATED)}:</b> {updated}")
    return "\n".join(lines)


def format_source_health(response: QueryResponse) -> str:
    if response.status == "no_data":
        return format_no_data(response)
    if response.status == "error":
        return format_error(response)

    lines = [screen_header(t.TITLE_HEALTH, "מצב אינגסטיה לפי מקור")]
    for row in (response.data or [])[:6]:
        name = esc(row.get("source_name") or "?")
        status = _status_label(row.get("latest_status"))
        ok = format_number(row.get("success_count"))
        fail = format_number(row.get("failure_count"))
        last_ok = format_timestamp(row.get("last_success_at"))
        lines.append(
            f"\n• <b>{name}</b> — {status}\n"
            f"   {esc(t.LABEL_SUCCESS)}: {ok} · {esc(t.LABEL_FAILURES)}: {fail}\n"
            f"   {esc(t.LABEL_UPDATED)}: {last_ok}"
        )
    return "\n".join(lines)


def format_anomalies(response: QueryResponse) -> str:
    if response.status == "no_data":
        return (
            f"{screen_header(t.TITLE_ANOMALIES)}\n"
            f"{esc(t.ANOMALY_BODY)}"
        )
    if response.status == "error":
        return format_error(response)

    lines = [screen_header(t.TITLE_ANOMALIES)]
    rows = response.data or []
    if not rows:
        return (
            f"{screen_header(t.TITLE_ANOMALIES)}\n"
            f"{esc(t.ANOMALY_BODY)}"
        )

    for row in rows[:10]:
        title = row.get("title") or row.get("island_code") or t.UNKNOWN_ISLAND
        severity = str(row.get("severity", "")).lower()
        if severity == "high":
            sev_label = esc(t.ANOMALY_SEVERITY_HIGH)
        elif severity == "medium":
            sev_label = esc(t.ANOMALY_SEVERITY_MEDIUM)
        else:
            sev_label = esc(severity or "?")
        lines.append(
            f"\n<b>{esc(title)}</b> ({esc(row.get('island_code', ''))})\n"
            f"   {esc(t.LABEL_PEAK_CCU)}: {format_number(row.get('peak_ccu'))}\n"
            f"   {esc(t.LABEL_SEVERITY)}: {sev_label}\n"
            f"   {esc(t.LABEL_TIME)}: {format_timestamp(row.get('metric_timestamp'))}\n"
            f"   Δ%: {_format_pct_change(row.get('pct_change_from_previous'))}"
        )
    return "\n".join(lines)


def format_avg_today(response: QueryResponse) -> str:
    if response.status == "no_data":
        return format_no_data(response)
    if response.status == "error":
        return format_error(response)

    row = (response.data or [{}])[0]
    period = str(row.get("period_label") or "today")
    period_note = (
        "היום (UTC)"
        if period == "today"
        else "תאריך אחרון זמין בנתונים"
    )
    body = (
        f"📊 <b>ממוצע Peak CCU:</b> {format_number(row.get('avg_peak_ccu'), decimals=1)}\n"
        f"🪣 <b>דליות שעה:</b> {format_number(row.get('hourly_buckets'))}\n"
        f"🕐 <b>שעה אחרונה:</b> {format_timestamp(row.get('latest_hour'))}\n"
        f"📅 <b>תקופה:</b> {esc(period_note)}"
    )
    return f"{screen_header(t.TITLE_AVG_TODAY)}\n{body}"


def format_menu_response(response: QueryResponse) -> str:
    """Route QueryResponse to the appropriate Hebrew formatter."""
    formatters: Dict[str, Callable[[QueryResponse], str]] = {
        "get_current_ccu": format_current_activity,
        "get_top_islands": format_top_islands,
        "get_shop_rarity_distribution": format_shop_summary,
        "get_source_health": format_source_health,
        "get_recent_anomalies": format_anomalies,
        "get_avg_today": format_avg_today,
        "help": lambda _r: help_text(),
    }
    formatter = formatters.get(response.query_name, format_query_response)
    return formatter(response)


def format_query_response(response: QueryResponse) -> str:
    """Generic fallback formatter."""
    if response.status == "no_data":
        return format_no_data(response)
    if response.status == "error":
        return format_error(response)
    rows: List[Any] = response.data or []
    if not rows:
        return format_no_data(response)
    lines = [screen_header(response.query_name)]
    for row in rows[:8]:
        if isinstance(row, dict):
            parts = " · ".join(f"{esc(k)}: {esc(v)}" for k, v in row.items())
            lines.append(f"\n• {parts}")
    if len(rows) > 8:
        lines.append(f"\n<i>+{len(rows) - 8} נוספים</i>")
    return "\n".join(lines)


# Re-export keyboards for handlers
__all__ = [
    "welcome_text",
    "help_text",
    "unknown_input_text",
    "main_menu_keyboard",
    "back_menu_keyboard",
    "format_menu_response",
    "format_no_data",
    "format_error",
]
