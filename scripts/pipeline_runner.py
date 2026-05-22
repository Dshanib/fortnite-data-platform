"""Shared subprocess helpers for demo and continuous refresh scripts."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Sequence

from scripts._script_runtime import ROOT, safe_print

SCRIPTS_DIR = ROOT / "scripts"


class StepFailed(RuntimeError):
    """Raised when a critical pipeline step exits non-zero."""

    def __init__(self, step: str, code: int, detail: str = "") -> None:
        self.step = step
        self.code = code
        self.detail = detail
        super().__init__(f"{step} failed (exit {code}){': ' + detail if detail else ''}")


def run_python_script(
    script_name: str,
    *args: str,
    env: Optional[dict] = None,
    critical: bool = True,
) -> int:
    """Run a script under scripts/ with the current interpreter."""
    script_path = SCRIPTS_DIR / script_name
    if not script_path.is_file():
        raise FileNotFoundError(f"Script not found: {script_path}")

    cmd: List[str] = [sys.executable, str(script_path), *args]
    merged = os.environ.copy()
    if env:
        merged.update(env)

    safe_print(f"\n>>> {' '.join(cmd)}")
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(ROOT),
            env=merged,
            check=False,
        )
    except OSError as exc:
        if critical:
            raise StepFailed(script_name, 1, str(exc)) from exc
        safe_print(f"  skipped ({exc})")
        return 1

    if completed.returncode != 0 and critical:
        raise StepFailed(script_name, completed.returncode)
    return completed.returncode


def run_module(
    module: str,
    *args: str,
    critical: bool = True,
) -> int:
    """Run python -m <module> from project root."""
    cmd: List[str] = [sys.executable, "-m", module, *args]
    safe_print(f"\n>>> {' '.join(cmd)}")
    completed = subprocess.run(cmd, cwd=str(ROOT), check=False)
    if completed.returncode != 0 and critical:
        raise StepFailed(module, completed.returncode)
    return completed.returncode


def kafka_topics_from_settings() -> Sequence[str]:
    from config.settings import get_settings

    s = get_settings()
    return (
        s.kafka_topic_shop,
        s.kafka_topic_cosmetics,
        s.kafka_topic_islands,
        s.kafka_topic_island_metrics,
        s.kafka_topic_ingestion_status,
    )
