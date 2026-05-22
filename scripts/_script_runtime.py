"""Shared bootstrap for CLI scripts (path, env, UTF-8-safe stdout)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv


def _resolve_project_root() -> Path:
    """Project root for host CLI, Airflow container, or explicit override."""
    override = (
        os.getenv("FORTNITE_PROJECT_ROOT")
        or os.getenv("AIRFLOW_PROJECT_ROOT")
        or ""
    ).strip()
    if override:
        return Path(override).resolve()
    return Path(__file__).resolve().parent.parent


ROOT = _resolve_project_root()

_MINIMAL_ENV = {
    "KAFKA_BOOTSTRAP_SERVERS": "localhost:9092",
    "MINIO_PROFILE": "internal",
    "MINIO_ENDPOINT": "http://localhost:9000",
    "MINIO_ACCESS_KEY": "x",
    "MINIO_SECRET_KEY": "x",
    "MINIO_BUCKET": "fortnite-data",
    "TELEGRAM_BOT_TOKEN": "test",
}


def bootstrap() -> Path:
    """Prepare script environment; return project root."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    load_dotenv(ROOT / ".env")
    for key, value in _MINIMAL_ENV.items():
        os.environ.setdefault(key, value)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    return ROOT


def safe_print(message: str) -> None:
    """Print text without failing on Windows console encoding."""
    try:
        print(message)
    except UnicodeEncodeError:
        encoding = sys.stdout.encoding or "utf-8"
        print(message.encode(encoding, errors="replace").decode(encoding, errors="replace"))
