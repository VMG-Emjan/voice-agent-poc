"""Local-LLM NLU provider via an OpenAI-compatible endpoint (Ollama).

Used only with `--nlu local-llm`. The LLM returns JSON matching the intent schema;
we validate it with NLUResult.from_json, so a malformed/hallucinated response falls
back safely to UNKNOWN. Requires a running local endpoint; needs no cloud API key.
"""

from __future__ import annotations

import json
from datetime import datetime

from ..schemas import NLUResult
from ..settings import KNOWN_DEPARTMENTS, Settings

_SYSTEM = (
    "You are an NLU parser for a voice receptionist. "
    "Return ONLY a JSON object, no prose, with keys: "
    'intent (one of book_appointment, route_call, faq, cancel, unknown), '
    'slots (object with date, time, name, department; use null when absent), '
    "and confidence (0..1). "
    f"Valid departments: {', '.join(KNOWN_DEPARTMENTS)}. "
    "Dates as YYYY-MM-DD and times as HH:MM (24h) when the user is explicit; "
    "otherwise null."
)


def make_nlu(settings: Settings | None = None):
    """Build a callable (text, now) -> NLUResult backed by the local LLM.

    Import of httpx is deferred so the deterministic core has zero dependencies.
    """
    settings = settings or Settings.from_env()
    try:
        import httpx  # noqa: F401
    except ImportError as e:  # pragma: no cover - exercised only in llm extra
        raise RuntimeError(
            "local-llm NLU needs the 'llm' extra: pip install '.[llm]'"
        ) from e

    def nlu(text: str, now: datetime) -> NLUResult:
        import httpx

        payload = {
            "model": settings.llm_model,
            "messages": [
                {"role": "system", "content": _SYSTEM},
                {"role": "system", "content": f"Current date: {now.date().isoformat()}."},
                {"role": "user", "content": text},
            ],
            "temperature": 0,
            "stream": False,
        }
        try:
            resp = httpx.post(
                f"{settings.llm_base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
        except Exception:
            # Endpoint down / bad response -> safe fallback, honest low confidence.
            return NLUResult(raw=text)
        return NLUResult.from_json(_extract_json(content))

    return nlu


def _extract_json(content: str) -> str:
    """Pull the first {...} block out of an LLM response that may wrap it in prose."""
    start, depth = content.find("{"), 0
    if start == -1:
        return "{}"
    for i in range(start, len(content)):
        if content[i] == "{":
            depth += 1
        elif content[i] == "}":
            depth -= 1
            if depth == 0:
                candidate = content[start : i + 1]
                try:
                    json.loads(candidate)
                    return candidate
                except json.JSONDecodeError:
                    return "{}"
    return "{}"
