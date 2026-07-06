"""Deterministic date/time normalization (TR + EN), clock-injectable.

Tests pass an explicit `now` so results never depend on the system clock. Ambiguous
phrases ("afternoon", "öğleden sonra") return None for that field so the dialog asks
a clarifying question instead of guessing.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta

# --- month names -------------------------------------------------------------
_MONTHS = {
    # English
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
    # Turkish
    "ocak": 1, "şubat": 2, "subat": 2, "mart": 3, "nisan": 4, "mayıs": 5, "mayis": 5,
    "haziran": 6, "temmuz": 7, "ağustos": 8, "agustos": 8, "eylül": 9, "eylul": 9,
    "ekim": 10, "kasım": 11, "kasim": 11, "aralık": 12, "aralik": 12,
}

# --- spelled-out hours (1..12), TR + EN -------------------------------------
_HOUR_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "bir": 1, "iki": 2, "üç": 3, "uc": 3, "dört": 4, "dort": 4, "beş": 5, "bes": 5,
    "altı": 6, "alti": 6, "yedi": 7, "sekiz": 8, "dokuz": 9,
    "onbir": 11, "oniki": 12,
    # NOTE: bare "on" (Turkish 10) is intentionally omitted — it collides with the
    # English preposition "on" (e.g. "on 2026-07-12"). Use a digit ("10") instead.
}

_AFTERNOON_MARKERS = ("pm", "öğleden sonra", "ogleden sonra", "afternoon", "akşam", "aksam")
_MORNING_MARKERS = ("am", "sabah", "öğleden önce", "ogleden once", "morning")


def normalize_date(text: str, now: datetime) -> str | None:
    """Return an ISO date 'YYYY-MM-DD' or None if not confidently determinable."""
    t = text.lower().strip()
    today = now.date()

    if re.search(r"\b(today|bugün|bugun)\b", t):
        return today.isoformat()
    if re.search(r"\b(tomorrow|yarın|yarin)\b", t):
        return (today + timedelta(days=1)).isoformat()
    if re.search(r"\b(day after tomorrow|öbür gün|obur gun)\b", t):
        return (today + timedelta(days=2)).isoformat()

    # ISO 2026-07-12
    m = re.search(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", t)
    if m:
        return _safe_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))

    # DD.MM.YYYY / DD/MM/YYYY / DD-MM (year optional -> next occurrence)
    m = re.search(r"\b(\d{1,2})[./](\d{1,2})(?:[./](\d{2,4}))?\b", t)
    if m:
        day, month = int(m.group(1)), int(m.group(2))
        year = _year_or_next(month, day, today, m.group(3))
        return _safe_date(year, month, day)

    # "12 July" / "July 12" / "12 Temmuz"
    m = re.search(r"\b(\d{1,2})\s+([a-zçğıöşü]+)\b", t)
    if m and m.group(2) in _MONTHS:
        day, month = int(m.group(1)), _MONTHS[m.group(2)]
        return _safe_date(_year_or_next(month, day, today, None), month, day)
    m = re.search(r"\b([a-zçğıöşü]+)\s+(\d{1,2})\b", t)
    if m and m.group(1) in _MONTHS:
        month, day = _MONTHS[m.group(1)], int(m.group(2))
        return _safe_date(_year_or_next(month, day, today, None), month, day)

    return None


def normalize_time(text: str) -> str | None:
    """Return 'HH:MM' (24h) or None if ambiguous/absent."""
    t = text.lower().strip()
    pm = any(mk in t for mk in _AFTERNOON_MARKERS)
    am = any(mk in t for mk in _MORNING_MARKERS)

    # 14:30 / 14.30 / 9:00
    m = re.search(r"\b(\d{1,2})[:.](\d{2})\b", t)
    if m:
        h, mi = int(m.group(1)), int(m.group(2))
        if 0 <= h <= 23 and 0 <= mi <= 59:
            return f"{h:02d}:{mi:02d}"

    # "3 pm" / "saat 3" / "at 3"
    m = re.search(r"\b(?:saat|at|@)?\s*(\d{1,2})\s*(am|pm)?\b", t)
    if m and (m.group(2) or "saat" in t or "at " in t or re.search(r"\bat\b", t)):
        h = int(m.group(1))
        if 1 <= h <= 12:
            return _apply_meridiem(h, pm=pm or m.group(2) == "pm", am=am or m.group(2) == "am")
        if 0 <= h <= 23:
            return f"{h:02d}:00"

    # spelled-out: "saat üç", "three pm"
    for word, h in _HOUR_WORDS.items():
        if re.search(rf"\b{re.escape(word)}\b", t):
            return _apply_meridiem(h, pm=pm, am=am)

    return None


def _apply_meridiem(h: int, pm: bool, am: bool) -> str | None:
    if pm and h < 12:
        h += 12
    elif am and h == 12:
        h = 0
    elif not pm and not am and h < 8:
        # Bare "3" with no am/pm and no 24h form is ambiguous for early hours.
        return None
    return f"{h:02d}:00"


def _safe_date(year: int, month: int, day: int) -> str | None:
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def _year_or_next(month: int, day: int, today: date, group: str | None) -> int:
    if group:
        y = int(group)
        return y + 2000 if y < 100 else y
    # No year given: pick this year, or next year if the date already passed.
    try:
        candidate = date(today.year, month, day)
    except ValueError:
        return today.year
    return today.year if candidate >= today else today.year + 1
