"""Tests for bot single-instance lock."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from bot.single_instance import _pid_alive, ensure_single_instance


def test_pid_alive_current_process() -> None:
    assert _pid_alive(os.getpid()) is True


def test_pid_alive_dead_process() -> None:
    assert _pid_alive(999999) is False


def test_ensure_single_instance_creates_lock(tmp_path: Path) -> None:
    lock = tmp_path / "bot.lock"
    path = ensure_single_instance(lock)
    assert path == lock
    assert lock.read_text(encoding="utf-8").strip() == str(os.getpid())


def test_ensure_single_instance_rejects_second_live_holder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    lock = tmp_path / "bot.lock"
    ensure_single_instance(lock)

    def fake_alive(pid: int) -> bool:
        return pid == os.getpid()

    monkeypatch.setattr("bot.single_instance._pid_alive", fake_alive)
    with pytest.raises(SystemExit, match="already running"):
        ensure_single_instance(lock)


def test_stale_lock_is_replaced(tmp_path: Path) -> None:
    lock = tmp_path / "bot.lock"
    lock.write_text("999999", encoding="utf-8")
    ensure_single_instance(lock)
    assert lock.read_text(encoding="utf-8").strip() == str(os.getpid())
