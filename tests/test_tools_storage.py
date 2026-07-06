"""Tool + storage guards: availability, double-booking, tool errors, isolation."""

from __future__ import annotations

from pathlib import Path

import pytest

from conftest import REPO_ROOT
from voice_agent.storage import AppointmentStore, DoubleBookingError
from voice_agent.tools import Tools

DATE = "2026-07-12"


def make_tools(data_dir: Path) -> Tools:
    store = AppointmentStore(data_dir / "appointments.json")
    return Tools(data_dir / "calendar.example.json", store)


def test_check_availability_excludes_blocked(data_dir):
    tools = make_tools(data_dir)
    free = tools.check_availability(DATE).data["free"]
    assert "14:00" not in free  # blocked in fixture
    assert "15:00" in free


def test_book_slot_writes_and_blocks_double(data_dir):
    tools = make_tools(data_dir)
    ok = tools.book_slot("Ada", DATE, "15:00")
    assert ok.ok
    # Same slot again -> availability now excludes it -> refused.
    again = tools.book_slot("Bo", DATE, "15:00")
    assert not again.ok


def test_storage_raises_on_double_booking(data_dir):
    store = AppointmentStore(data_dir / "appointments.json")
    store.book("Ada", f"{DATE}T15:00")
    with pytest.raises(DoubleBookingError):
        store.book("Bo", f"{DATE}T15:00")


def test_book_blocked_slot_is_tool_error(data_dir):
    tools = make_tools(data_dir)
    res = tools.book_slot("Cy", DATE, "14:00")  # blocked slot
    assert not res.ok
    assert "not available" in res.message.lower()


def test_route_unknown_department_tool_error(data_dir):
    tools = make_tools(data_dir)
    assert not tools.route_call("astronauts").ok
    assert tools.route_call("sales").ok


def test_tests_never_touch_real_appointments_file(appointments_file):
    # The store used by tests lives under tmp, not the repo's data dir.
    assert "tmp" in str(appointments_file).lower() or "temp" in str(appointments_file).lower()
    real = REPO_ROOT / "data" / "appointments.json"
    assert not real.exists(), "real data/appointments.json must not be created by tests"
