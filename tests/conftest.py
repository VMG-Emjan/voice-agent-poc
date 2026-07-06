"""Shared fixtures. Every test runs against a tmp data dir so the real
data/appointments.json is never touched, and against a fixed clock so results
never depend on the system time.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

import pytest

from voice_agent.agent import build_agent
from voice_agent.logging import EventLog

# Monday 2026-07-06, 10:00 local. All relative-date tests key off this.
FIXED_NOW = datetime(2026, 7, 6, 10, 0, 0)

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def now():
    return FIXED_NOW


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    """A writable copy of the demo calendar in an isolated tmp dir."""
    d = tmp_path / "data"
    d.mkdir()
    shutil.copy(REPO_ROOT / "data" / "calendar.example.json", d / "calendar.example.json")
    return d


@pytest.fixture
def agent(data_dir: Path):
    return build_agent(
        nlu_mode="deterministic",
        data_dir=data_dir,
        now_provider=lambda: FIXED_NOW,
        log=EventLog(),
    )


@pytest.fixture
def appointments_file(data_dir: Path) -> Path:
    return data_dir / "appointments.json"


def read_appointments(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))
