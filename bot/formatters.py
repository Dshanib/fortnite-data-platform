"""Format QueryService responses for Telegram (Hebrew UI, HTML)."""

from __future__ import annotations

from typing import Any, Callable, Dict, List

from common.models import QueryResponse

from bot import copy_he as t
from bot.ui import (
    back_menu_keyboard,
    category_label,
    esc,
    format_number,
    format_timestamp,
    main_menu_keyboard,
    screen_header,
    shop_back_keyboard,
)


def welcome_text() -> str:
    return f"<b>🎮 {esc(t.WELCOME_TITLE)}</b>\n\n{t.WELCOME_BODY}"


def activity_hub_text() -> str:
    return (
        f"{screen_header(t.ACTIVITY_HUB_TITLE, t.ACTIVITY_HUB_BODY)}\n"
        f"<i>{esc(t.MENU_PROMPT)}</i>"
    )


def shop_hub_text() -> str:
    return (
        f"{screen_header(t.SHOP_HUB_TITLE, t.SHOP_HUB_BODY)}\n"
        f"<i>{esc(t.MENU_PROMPT)}</i>"
    )


def help_text() -> str:
    return f"<b>{esc(t.HELP_TITLE)}</b>\n{t.HELP_BODY}"


def unknown_input_text() -> str:
    return esc(t.UNKNOWN_INPUT)


def format_no_data(response: QueryResponse) -> str:
    detail = response.message or t.NO_DATA_HINT
    return f"{screen_header(t.NO_DATA_TITLE)}\n{esc(detail)}"


def format_error(response: QueryResponse) -> str:
    detail = response.message or t.ERROR_HINT
    return f"{screen_header(t.ERROR_TITLE)}\n{esc(detail)}"


def _rarity_label(raw: Any) -> str:
    key = str(raw or "unknown").strip().lower()
    return t.RARITY_LABELS.get(key, esc(raw))


def _format_pct_change(value: Any) -> str:
    if value is None:
        return "—"
    try:
        return f"{format_number(float(value) * 100.0, decimals=0)}%"
    except (TypeError, ValueError):
        return "—"


def _updated_line(value: Any) -> str:
    if not value:
        return ""
    return f"🕐 <b>{esc(t.LABEL_UPDATED)}:</b> {format_timestamp(value)}"


def format_players_online(response: QueryResponse) -> str:
    if response.status == "no_data":
        return format_no_data(response)
    if response.status == "error":
        return format_error(response)

    row = (response.data or [{}])[0]
    lines = [
        screen_header(t.TITLE_PLAYERS_NOW),
        f"📅 <b>{esc(t.LABEL_METRIC_DAY)}:</b> {format_timestamp(row.get('metric_date'))}",
        "",
        f"👥 <b>{esc(t.LABEL_ACTIVE_TODAY)}:</b> "
        f"{format_number(row.get('active_players_today') or row.get('unique_players_today'))}",
        f"▶️ <b>{esc(t.LABEL_PLAYS_TODAY)}:</b> {format_number(row.get('plays_today'))}",
        f"🗺️ <b>{esc(t.LABEL_ISLANDS_TOTAL)}:</b> {format_number(row.get('islands_with_data'))}",
        f"📈 <b>{esc(t.LABEL_PEAK_HOUR)}:</b> {format_number(row.get('peak_ccu_today'))}",
    ]
    updated = _updated_line(row.get("data_as_of"))
    if updated:
        lines.extend(["", updated])
    return "\n".join(lines)


def format_most_active_island(response: QueryResponse) -> str:
    if response.status == "no_data":
        return format_no_data(response)
    if response.status == "error":
        return format_error(response)

    row = (response.data or [{}])[0]
    title = row.get("title") or t.UNKNOWN_ISLAND
    code = row.get("island_code", "?")
    creator = row.get("creator_code")

    lines = [
        screen_header(t.TITLE_MOST_ACTIVE),
        f"🥇 <b>{esc(title)}</b>",
        f"🔑 <b>{esc(t.LABEL_CODE)}:</b> <code>{esc(code)}</code>",
    ]
    if creator:
        lines.append(f"👤 <b>{esc(t.LABEL_CREATOR)}:</b> {esc(creator)}")
    lines.extend(
        [
            "",
            f"👥 <b>{esc(t.LABEL_PEAK_CCU)}:</b> {format_number(row.get('peak_ccu'))}",
            f"🎮 <b>{esc(t.LABEL_PLAYERS)}:</b> {format_number(row.get('unique_players'))}",
            f"▶️ <b>{esc(t.LABEL_PLAYS)}:</b> {format_number(row.get('plays'))}",
            f"⏱️ <b>{esc(t.LABEL_MINUTES)}:</b> {format_number(row.get('minutes_played'))}",
        ]
    )
    updated = _updated_line(row.get("data_as_of") or row.get("latest_metric_timestamp"))
    if updated:
        lines.extend(["", updated])
    return "\n".join(lines)


def format_current_activity(response: QueryResponse) -> str:
    return format_most_active_island(response)


def format_top_islands(response: QueryResponse) -> str:
    if response.status == "no_data":
        return format_no_data(response)
    if response.status == "error":
        return format_error(response)

    rows = response.data or []
    lines = [screen_header(t.TITLE_TOP_ISLANDS)]

    if not rows:
        lines.append(esc(t.NO_DATA_HINT))
        return "\n".join(lines)

    first = rows[0]
    if first.get("metric_date"):
        lines.append(
            f"📅 <b>{esc(t.LABEL_METRIC_DAY)}:</b> {format_timestamp(first['metric_date'])}"
        )
    total = first.get("total_islands") or len(rows)
    lines.append(f"🗺️ <b>{esc(t.LABEL_ISLANDS_TOTAL)}:</b> {format_number(total)}\n")

    updated = _updated_line(first.get("data_as_of"))
    if updated:
        lines.append(updated + "\n")

    display_cap = 25
    for row in rows[:display_cap]:
        rank = row.get("rank", "?")
        title = row.get("title") or row.get("island_code") or t.UNKNOWN_ISLAND
        code = row.get("island_code", "?")
        peak = format_number(row.get("peak_ccu"))
        players = format_number(row.get("unique_players"))
        lines.append(
            f"\n<b>#{esc(rank)}</b> {esc(title)} · <code>{esc(code)}</code>\n"
            f"   {esc(t.LABEL_PEAK_CCU)}: {peak} · {esc(t.LABEL_PLAYERS)}: {players}"
        )

    if total and int(total) > display_cap:
        lines.append(
            f"\n<i>+{int(total) - display_cap} {esc(t.TOP_ISLANDS_MORE)}</i>"
        )
    return "\n".join(lines)


def format_shop_category_items(response: QueryResponse, *, category: str = "") -> str:
    if response.status == "no_data":
        return format_no_data(response)
    if response.status == "error":
        return format_error(response)

    rows = response.data or []
    cat_label = category_label(category or (rows[0].get("category") if rows else "unknown"))
    lines = [screen_header(f"{t.TITLE_SHOP_CATEGORY}: {cat_label}")]

    if not rows:
        lines.append(esc(t.NO_DATA_HINT))
        return "\n".join(lines)

    total_in_category = rows[0].get("total_in_category") or len(rows)
    lines.append(f"📦 <b>{esc(t.LABEL_ITEMS_TOTAL)}:</b> {format_number(total_in_category)}")
    if rows[0].get("snapshot_date"):
        lines.append(
            f"📅 <b>{esc(t.LABEL_SNAPSHOT)}:</b> {format_timestamp(rows[0]['snapshot_date'])}"
        )
    lines.append("")

    display_cap = 8
    for row in rows[:display_cap]:
        name = str(row.get("item_name") or row.get("dev_name") or "?")
        if len(name) > 42:
            name = name[:39] + "..."
        rarity = _rarity_label(row.get("rarity"))
        price = format_number(row.get("final_price"))
        lines.append(f"• <b>{esc(name)}</b> ({rarity}) — {price} V-Bucks")

    shown = min(len(rows), display_cap)
    if total_in_category and int(total_in_category) > shown:
        lines.append(
            f"\n<i>+{int(total_in_category) - shown} {esc(t.SHOP_ITEMS_MORE)}</i>"
        )

    text = "\n".join(lines)
    if len(text) > 3900:
        text = text[:3900] + "\n…"
    return text


def format_shop_summary(response: QueryResponse) -> str:
    if response.status == "no_data":
        return format_no_data(response)
    if response.status == "error":
        return format_error(response)

    snap = "—"
    lines = [screen_header(t.TITLE_SHOP)]
    for row in response.data or []:
        rarity = _rarity_label(row.get("rarity"))
        count = format_number(row.get("item_count"))
        share = format_number(row.get("share_pct"), decimals=1)
        if row.get("snapshot_date"):
            snap = format_timestamp(row.get("snapshot_date"))
        lines.append(f"\n• <b>{rarity}</b> — {count} ({share}%)")

    lines.append(f"\n📅 <b>{esc(t.LABEL_SNAPSHOT)}:</b> {snap}")
    return "\n".join(lines)


def format_source_health(response: QueryResponse) -> str:
    if response.status == "no_data":
        return format_no_data(response)
    if response.status == "error":
        return format_error(response)

    lines = [screen_header(t.TITLE_HEALTH)]
    for row in (response.data or [])[:6]:
        name = esc(row.get("source_name") or "?")
        status = str(row.get("latest_status") or "?")
        ok = format_number(row.get("success_count"))
        fail = format_number(row.get("failure_count"))
        lines.append(
            f"\n• <b>{name}</b> — {esc(status)}\n"
            f"   הצלחות: {ok} · כשלונות: {fail}"
        )
    return "\n".join(lines)


def format_anomalies(response: QueryResponse) -> str:
    if response.status == "no_data":
        return f"{screen_header(t.TITLE_ANOMALIES)}\n{esc(t.ANOMALY_BODY)}"
    if response.status == "error":
        return format_error(response)

    lines = [screen_header(t.TITLE_ANOMALIES)]
    rows = response.data or []
    if not rows:
        return f"{screen_header(t.TITLE_ANOMALIES)}\n{esc(t.ANOMALY_BODY)}"

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
    body = (
        f"📊 <b>ממוצע שחקנים מחוברים:</b> "
        f"{format_number(row.get('avg_peak_ccu'), decimals=1)}\n"
        f"🕐 <b>{esc(t.LABEL_TIME)}:</b> {format_timestamp(row.get('latest_hour'))}"
    )
    return f"{screen_header(t.TITLE_AVG_TODAY)}\n{body}"


def format_menu_response(
    response: QueryResponse,
    *,
    shop_category: str = "",
) -> str:
    """Route QueryResponse to the appropriate Hebrew formatter."""
    formatters: Dict[str, Callable[[QueryResponse], str]] = {
        "get_players_online_summary": format_players_online,
        "get_most_active_island": format_most_active_island,
        "get_current_ccu": format_current_activity,
        "get_top_islands": format_top_islands,
        "get_shop_rarity_distribution": format_shop_summary,
        "get_shop_items_by_category": lambda r: format_shop_category_items(
            r, category=shop_category
        ),
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
    return "\n".join(lines)


__all__ = [
    "welcome_text",
    "activity_hub_text",
    "shop_hub_text",
    "help_text",
    "unknown_input_text",
    "main_menu_keyboard",
    "back_menu_keyboard",
    "shop_back_keyboard",
    "format_menu_response",
    "format_no_data",
    "format_error",
]
