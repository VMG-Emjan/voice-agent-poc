"""Deterministic NLU provider. Offline, keyless — the default and CI-tested path."""

from __future__ import annotations

from datetime import datetime

from ..intents import parse
from ..schemas import NLUResult


def nlu(text: str, now: datetime) -> NLUResult:
    return parse(text, now)
