"""Structured event logging with secret redaction.

Emits newline-delimited JSON (session.jsonl) so real runs produce machine-checkable
evidence. Never logs raw API keys/tokens.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any

# Redact anything that looks like a key/token/secret in logged values.
_SECRET_RE = re.compile(
    r"(?i)(api[_-]?key|token|secret|authorization|bearer)\s*[:=]?\s*([A-Za-z0-9._\-]{6,})"
)


def redact(text: str) -> str:
    return _SECRET_RE.sub(lambda m: f"{m.group(1)}=***REDACTED***", text)


def _scrub(value: Any) -> Any:
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, dict):
        return {k: _scrub(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_scrub(v) for v in value]
    return value


@dataclass
class EventLog:
    """Collects structured events; can be written to a .jsonl file."""

    events: list[dict] = field(default_factory=list)
    _clock: Any = time.time

    def emit(self, event_type: str, **data: Any) -> dict:
        entry = {"ts": round(self._clock(), 3), "event": event_type, **_scrub(data)}
        self.events.append(entry)
        return entry

    def to_jsonl(self) -> str:
        return "\n".join(json.dumps(e, ensure_ascii=False) for e in self.events)
