"""Appointment persistence. Atomic writes, double-booking guard.

Tests point `AppointmentStore` at a tmp dir so the real data/appointments.json is
never touched.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


class DoubleBookingError(Exception):
    """Raised when a slot (datetime) is already taken."""


class AppointmentStore:
    def __init__(self, path: str | os.PathLike[str]):
        self.path = Path(path)

    def _load(self) -> list[dict]:
        if not self.path.exists():
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
        return data if isinstance(data, list) else []

    def all(self) -> list[dict]:
        return self._load()

    def is_taken(self, datetime_iso: str) -> bool:
        return any(a.get("datetime") == datetime_iso for a in self._load())

    def book(self, name: str, datetime_iso: str, department: str | None = None) -> dict:
        records = self._load()
        if any(a.get("datetime") == datetime_iso for a in records):
            raise DoubleBookingError(datetime_iso)
        record = {"name": name, "datetime": datetime_iso, "department": department}
        records.append(record)
        self._atomic_write(records)
        return record

    def _atomic_write(self, records: list[dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(records, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)  # atomic on POSIX and Windows
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
