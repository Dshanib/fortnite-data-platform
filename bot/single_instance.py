"""Ensure at most one Telegram bot process runs per lock file."""

from __future__ import annotations

import atexit
import os
from pathlib import Path

from common.logging import get_logger

logger = get_logger(__name__)

_DEFAULT_LOCK = Path("data/.telegram_bot.lock")
_lock_path: Path | None = None


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # Process exists but belongs to another user/session.
        return True
    except OSError:
        return False
    return True


def _read_lock_pid(lock_path: Path) -> int | None:
    try:
        raw = lock_path.read_text(encoding="utf-8").strip()
        return int(raw)
    except (OSError, ValueError):
        return None


def _release_lock(lock_path: Path) -> None:
    try:
        if lock_path.exists():
            current = _read_lock_pid(lock_path)
            if current is None or current == os.getpid():
                lock_path.unlink()
    except OSError as exc:
        logger.warning("Could not remove bot lock %s: %s", lock_path, exc)


def ensure_single_instance(lock_path: Path | None = None) -> Path:
    """
    Acquire a PID lock file. Exit the process if another live bot holds it.

    Stale locks (dead PID) are removed automatically.
    """
    global _lock_path
    path = lock_path or _DEFAULT_LOCK
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        existing = _read_lock_pid(path)
        if existing is not None and _pid_alive(existing):
            raise SystemExit(
                f"Telegram bot already running (PID {existing}). "
                f"Stop that process first, or run: python scripts/run_bot.py"
            )
        path.unlink(missing_ok=True)

    try:
        fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        try:
            os.write(fd, str(os.getpid()).encode("ascii"))
        finally:
            os.close(fd)
    except FileExistsError:
        existing = _read_lock_pid(path)
        if existing is not None and _pid_alive(existing):
            raise SystemExit(
                f"Telegram bot already running (PID {existing}). "
                f"Stop that process first, or run: python scripts/run_bot.py"
            )
        path.unlink(missing_ok=True)
        return ensure_single_instance(path)

    _lock_path = path
    atexit.register(_release_lock, path)
    logger.info("Bot single-instance lock acquired: %s (pid=%s)", path, os.getpid())
    return path
