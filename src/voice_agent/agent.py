"""Factory: wire an NLU provider + tools + storage into a DialogManager."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from .dialog import DialogManager
from .logging import EventLog
from .providers import deterministic
from .settings import Settings
from .storage import AppointmentStore
from .tools import Tools


def build_agent(
    nlu_mode: str = "deterministic",
    data_dir: str | Path = "data",
    now_provider: Callable[[], datetime] | None = None,
    log: EventLog | None = None,
    settings: Settings | None = None,
) -> DialogManager:
    data_dir = Path(data_dir)
    calendar = data_dir / "calendar.example.json"
    store = AppointmentStore(data_dir / "appointments.json")
    tools = Tools(calendar, store)

    if nlu_mode == "local-llm":
        from .providers.openai_compatible import make_nlu

        nlu = make_nlu(settings or Settings.from_env())
    else:
        nlu = deterministic.nlu

    return DialogManager(nlu=nlu, tools=tools, log=log or EventLog(), now_provider=now_provider)
