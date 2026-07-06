"""Tool layer. The dialog state machine calls these; the LLM never does directly.

- check_availability(date): reads a LOCAL DEMO CALENDAR fixture (not a "fake" calendar).
- book_slot(name, datetime): atomic write via AppointmentStore, double-booking guarded.
- route_call(department): Level-A returns a VERIFIED routing DECISION (simulation),
  not a real telephony transfer. Real PSTN/LiveKit handoff is opt-in and out of scope
  for the deterministic core.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from .settings import CLOSE_HOUR, KNOWN_DEPARTMENTS, OPEN_HOUR, SLOT_MINUTES
from .storage import AppointmentStore, DoubleBookingError


@dataclass
class ToolResult:
    ok: bool
    kind: str
    data: dict
    message: str


class Tools:
    def __init__(self, calendar_path: str | Path, store: AppointmentStore):
        self.calendar_path = Path(calendar_path)
        self.store = store

    # --- availability -------------------------------------------------------
    def _calendar(self) -> dict:
        if not self.calendar_path.exists():
            return {}
        try:
            data = json.loads(self.calendar_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
        return data if isinstance(data, dict) else {}

    def check_availability(self, date_iso: str) -> ToolResult:
        cal = self._calendar()
        # Blocked slots come from the fixture; booked slots come from runtime store.
        blocked = set(cal.get("blocked", {}).get(date_iso, []))
        booked = {
            a["datetime"].split("T")[1][:5]
            for a in self.store.all()
            if a.get("datetime", "").startswith(date_iso) and "T" in a.get("datetime", "")
        }
        free = [s for s in _day_slots() if s not in blocked and s not in booked]
        msg = f"{len(free)} slot(s) free on {date_iso}." if free else f"No slots on {date_iso}."
        return ToolResult(
            ok=bool(free),
            kind="check_availability",
            data={"date": date_iso, "free": free, "blocked": sorted(blocked)},
            message=msg,
        )

    def suggest_alternatives(self, date_iso: str, time_hhmm: str, limit: int = 3) -> list[str]:
        avail = self.check_availability(date_iso).data["free"]
        if time_hhmm in avail:
            return [time_hhmm]
        # Nearest free slots by clock distance.
        target = _to_minutes(time_hhmm)
        ranked = sorted(avail, key=lambda s: abs(_to_minutes(s) - target))
        return ranked[:limit]

    # --- booking ------------------------------------------------------------
    def book_slot(self, name: str, date_iso: str, time_hhmm: str,
                  department: str | None = None) -> ToolResult:
        dt_iso = f"{date_iso}T{time_hhmm}"
        # Guard: slot must be free per the fixture too.
        if time_hhmm not in self.check_availability(date_iso).data["free"]:
            return ToolResult(False, "book_slot", {"datetime": dt_iso},
                              f"{time_hhmm} on {date_iso} is not available.")
        try:
            rec = self.store.book(name, dt_iso, department)
        except DoubleBookingError:
            return ToolResult(False, "book_slot", {"datetime": dt_iso},
                              f"{dt_iso} is already booked.")
        return ToolResult(True, "book_slot", rec, f"Booked {name} for {date_iso} {time_hhmm}.")

    # --- routing ------------------------------------------------------------
    def route_call(self, department: str | None) -> ToolResult:
        if department not in KNOWN_DEPARTMENTS:
            return ToolResult(False, "route_call", {"department": department},
                              f"Unknown department: {department!r}.")
        # Level-A: a routing DECISION, honestly labeled as a simulation target.
        return ToolResult(
            True, "route_call",
            {
                "department": department,
                "target": f"queue:{department}",
                "mode": "routing-decision-simulation",
            },
            f"Routing decision: connect to {department} (simulated queue target).",
        )


def _day_slots() -> list[str]:
    out: list[str] = []
    cur = datetime(2000, 1, 1, OPEN_HOUR, 0)
    end = datetime(2000, 1, 1, CLOSE_HOUR, 0)
    while cur < end:
        out.append(cur.strftime("%H:%M"))
        cur += timedelta(minutes=SLOT_MINUTES)
    return out


def _to_minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)
