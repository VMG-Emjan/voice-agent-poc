"""Deterministic NLU: rule-based intent + slot extraction (TR + EN).

This is the default `--nlu deterministic` provider. It is fully offline, needs no
API key, and is what CI tests. The local-LLM provider (providers/openai_compatible.py)
produces the same NLUResult shape but via an Ollama endpoint.
"""

from __future__ import annotations

import re
from datetime import datetime

from .datetimeparse import normalize_date, normalize_time
from .schemas import Intent, NLUResult
from .settings import KNOWN_DEPARTMENTS

_BOOK_RE = re.compile(
    r"\b(book|appointment|reserve|schedule|randevu|rezervasyon|ayır|ayir)\b", re.IGNORECASE
)
_ROUTE_RE = re.compile(
    r"\b(transfer|route|connect|reach|department|yönlendir|yonlendir|bağla|bagla|birim)\b",
    re.IGNORECASE,
)
_CANCEL_RE = re.compile(
    r"\b(cancel|nevermind|never mind|stop|iptal|vazge[çc]|boş ver|bos ver)\b", re.IGNORECASE
)
_FAQ_RE = re.compile(
    r"\b(hours|open|where|how much|price|question|saat ka[çc]|nerede|fiyat|soru)\b",
    re.IGNORECASE,
)

# Department synonyms -> canonical department.
_DEPT_SYNONYMS = {
    "sales": "sales", "satış": "sales", "satis": "sales", "sale": "sales",
    "support": "support", "destek": "support", "help": "support", "yardım": "support",
    "billing": "billing", "fatura": "billing", "payment": "billing", "ödeme": "billing",
    "reception": "reception", "resepsiyon": "reception", "front desk": "reception",
}

_NAME_RE = re.compile(
    r"\b(?:my name is|i am|i'm|this is|adım|adim|ben|ismim)\s+"
    r"([A-Za-zÇĞİÖŞÜçğıöşü]+(?:\s+[A-Za-zÇĞİÖŞÜçğıöşü]+)?)",
    re.IGNORECASE,
)


def parse(text: str, now: datetime | None = None) -> NLUResult:
    now = now or datetime.now()
    t = text.strip()
    lower = t.lower()

    intent = Intent.UNKNOWN
    confidence = 0.0

    if _CANCEL_RE.search(lower):
        intent, confidence = Intent.CANCEL, 0.9
    elif _BOOK_RE.search(lower):
        intent, confidence = Intent.BOOK_APPOINTMENT, 0.85
    elif _ROUTE_RE.search(lower) or _department_in(lower):
        intent, confidence = Intent.ROUTE_CALL, 0.8
    elif _FAQ_RE.search(lower):
        intent, confidence = Intent.FAQ, 0.75

    slots = {
        "date": normalize_date(t, now),
        "time": normalize_time(t),
        "name": _extract_name(t),
        "department": _department_in(lower),
    }

    # If we found booking-ish slots but no explicit verb, still lean to booking.
    if intent is Intent.UNKNOWN and (slots["date"] or slots["time"]):
        intent, confidence = Intent.BOOK_APPOINTMENT, 0.5

    return NLUResult(intent=intent, slots=slots, confidence=confidence, raw=t)


def _department_in(lower: str) -> str | None:
    for syn, canon in _DEPT_SYNONYMS.items():
        if re.search(rf"\b{re.escape(syn)}\b", lower):
            if canon in KNOWN_DEPARTMENTS:
                return canon
    return None


def _extract_name(text: str) -> str | None:
    m = _NAME_RE.search(text)
    if not m:
        return None
    name = m.group(1).strip()
    # Reject if it collided with a keyword (e.g. "I am booking").
    if _BOOK_RE.search(name) or _ROUTE_RE.search(name) or _CANCEL_RE.search(name):
        return None
    return name.title()
