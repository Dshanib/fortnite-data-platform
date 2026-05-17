"""Format query responses for Telegram."""

from __future__ import annotations

from typing import Any, List

from common.models import QueryResponse


def format_query_response(response: QueryResponse) -> str:
    """Convert QueryResponse to human-readable Telegram text."""
    if not response.success:
        return f"{response.query_name}: {response.message}"

    rows: List[Any] = response.data or []
    if not rows:
        return f"{response.query_name}: no data"

    lines = [response.query_name]
    for row in rows[:10]:
        parts = ", ".join(f"{k}={v}" for k, v in row.items())
        lines.append(f"- {parts}")
    if len(rows) > 10:
        lines.append(f"... and {len(rows) - 10} more")
    return "\n".join(lines)


def help_text() -> str:
    """Return bot help message."""
    return (
        "Fortnite DE Bot (Phase 1)\n\n"
        "Commands / keywords:\n"
        "- current ccu / players online\n"
        "- avg ccu today\n"
        "- anomaly check\n"
        "- shop summary / rarity\n"
        "- source health / status\n"
        "- help\n"
    )
