"""Clock-injected date/time normalization — deterministic, no system-clock dependence."""

from __future__ import annotations

from datetime import datetime

import pytest

from voice_agent.datetimeparse import normalize_date, normalize_time

NOW = datetime(2026, 7, 6, 10, 0, 0)  # Monday


@pytest.mark.parametrize(
    "text,expected",
    [
        ("today", "2026-07-06"),
        ("bugün", "2026-07-06"),
        ("tomorrow", "2026-07-07"),
        ("yarın", "2026-07-07"),
        ("2026-07-12", "2026-07-12"),
        ("12.07.2026", "2026-07-12"),
        ("12 July", "2026-07-12"),
        ("12 Temmuz", "2026-07-12"),
        ("July 12", "2026-07-12"),
    ],
)
def test_normalize_date(text, expected):
    assert normalize_date(text, NOW) == expected


def test_date_none_when_absent():
    assert normalize_date("just a random sentence", NOW) is None


@pytest.mark.parametrize(
    "text,expected",
    [
        ("15:00", "15:00"),
        ("at 3pm", "15:00"),
        ("saat 15:00", "15:00"),
        ("three pm", "15:00"),
        ("9:30", "09:30"),
    ],
)
def test_normalize_time(text, expected):
    assert normalize_time(text) == expected


@pytest.mark.parametrize("text", ["afternoon", "öğleden sonra", "sometime"])
def test_time_ambiguous_returns_none(text):
    # Ambiguous phrasing must NOT be guessed; dialog will ask a clarifying question.
    assert normalize_time(text) is None
