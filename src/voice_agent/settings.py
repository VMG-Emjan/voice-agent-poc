"""Runtime settings. Env-driven, safe defaults, no secrets committed."""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_TZ = "Europe/Istanbul"

# Departments the router knows about. Unknown -> route_call fails safely.
KNOWN_DEPARTMENTS = ("sales", "support", "billing", "reception")

# Business hours used by the demo calendar / alternative-slot suggestions.
OPEN_HOUR = 9
CLOSE_HOUR = 18
SLOT_MINUTES = 30


@dataclass(frozen=True)
class Settings:
    tz: str = DEFAULT_TZ
    llm_base_url: str = "http://localhost:11434/v1"
    llm_model: str = "llama3.2:1b"
    llm_api_key: str = "ollama"
    whisper_model: str = "base"
    piper_voice_model: str = "models/en_US-amy-medium.onnx"

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            tz=os.getenv("VOICE_AGENT_TZ", DEFAULT_TZ),
            llm_base_url=os.getenv("LOCAL_LLM_BASE_URL", "http://localhost:11434/v1"),
            llm_model=os.getenv("LOCAL_LLM_MODEL", "llama3.2:1b"),
            llm_api_key=os.getenv("LOCAL_LLM_API_KEY", "ollama"),
            whisper_model=os.getenv("WHISPER_MODEL", "base"),
            piper_voice_model=os.getenv("PIPER_VOICE_MODEL", "models/en_US-amy-medium.onnx"),
        )
