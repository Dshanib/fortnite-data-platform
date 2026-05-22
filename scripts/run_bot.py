#!/usr/bin/env python3
"""Stop duplicate bot.app processes and start a single Telegram bot instance."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts._script_runtime import bootstrap, safe_print

bootstrap()


def _pids_for_bot_app() -> list[int]:
    result = subprocess.run(
        [
            "wmic",
            "process",
            "where",
            "commandline like '%-m bot.app%'",
            "get",
            "processid",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    pids: list[int] = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if line.isdigit():
            pids.append(int(line))
    return pids


def stop_bot_instances() -> int:
    stopped = 0
    for pid in _pids_for_bot_app():
        proc = subprocess.run(
            ["taskkill", "/F", "/PID", str(pid)],
            capture_output=True,
            check=False,
        )
        if proc.returncode == 0:
            stopped += 1
    return stopped


def _python_executable() -> str:
    venv_python = _ROOT / ".venv" / "Scripts" / "python.exe"
    if venv_python.is_file():
        return str(venv_python)
    return sys.executable


def main() -> int:
    stopped = stop_bot_instances()
    if stopped:
        safe_print(f"Stopped {stopped} existing bot process(es).")

    python_exe = _python_executable()
    safe_print(f"Starting bot (Hebrew UI) with {python_exe}...")
    return subprocess.call(
        [python_exe, "-m", "bot.app"],
        cwd=str(_ROOT),
    )


if __name__ == "__main__":
    sys.exit(main())
