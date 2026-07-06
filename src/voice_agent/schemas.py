"""Typed intent/slot schema shared by every NLU provider.

The LLM (or deterministic parser) only ever PROPOSES one of these objects. The
dialog state machine validates it before acting. Nothing here writes files or
makes decisions on its own.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum


class Intent(str, Enum):
    BOOK_APPOINTMENT = "book_appointment"
    ROUTE_CALL = "route_call"
    FAQ = "faq"
    CANCEL = "cancel"
    UNKNOWN = "unknown"

    @classmethod
    def coerce(cls, value: object) -> Intent:
        """Map arbitrary/untrusted input to a known intent, defaulting to UNKNOWN."""
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            try:
                return cls(value.strip().lower())
            except ValueError:
                return cls.UNKNOWN
        return cls.UNKNOWN


# Known slot keys. Extra keys in untrusted input are dropped.
SLOT_KEYS = ("date", "time", "name", "department")

# Below this the state machine treats the parse as untrusted -> safe fallback.
MIN_CONFIDENCE = 0.35


@dataclass
class NLUResult:
    """Structured proposal from an NLU provider. Validated, never trusted blindly."""

    intent: Intent = Intent.UNKNOWN
    slots: dict[str, str | None] = field(default_factory=lambda: {k: None for k in SLOT_KEYS})
    confidence: float = 0.0
    raw: str | None = None  # original provider payload, for logging/debugging

    def __post_init__(self) -> None:
        # Normalize slots to exactly the known keys.
        clean: dict[str, str | None] = {k: None for k in SLOT_KEYS}
        for k in SLOT_KEYS:
            v = self.slots.get(k)
            if isinstance(v, str):
                v = v.strip() or None
            elif v is not None:
                v = str(v)
            clean[k] = v
        self.slots = clean
        self.intent = Intent.coerce(self.intent)
        try:
            self.confidence = max(0.0, min(1.0, float(self.confidence)))
        except (TypeError, ValueError):
            self.confidence = 0.0

    @property
    def trusted(self) -> bool:
        return self.intent is not Intent.UNKNOWN and self.confidence >= MIN_CONFIDENCE

    def to_dict(self) -> dict:
        return {
            "intent": self.intent.value,
            "slots": dict(self.slots),
            "confidence": round(self.confidence, 3),
        }

    @classmethod
    def from_json(cls, payload: str) -> NLUResult:
        """Parse an LLM's JSON string. Invalid JSON -> UNKNOWN, confidence 0 (safe fallback)."""
        try:
            data = json.loads(payload)
        except (json.JSONDecodeError, TypeError):
            return cls(intent=Intent.UNKNOWN, confidence=0.0, raw=str(payload))
        if not isinstance(data, dict):
            return cls(intent=Intent.UNKNOWN, confidence=0.0, raw=str(payload))
        slots_in = data.get("slots") if isinstance(data.get("slots"), dict) else {}
        return cls(
            intent=Intent.coerce(data.get("intent")),
            slots={k: slots_in.get(k) for k in SLOT_KEYS},
            confidence=data.get("confidence", 0.0),
            raw=payload if isinstance(payload, str) else str(payload),
        )
