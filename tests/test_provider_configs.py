"""Validate provider config JSON: parseable + required keys + tools match core.

These are the only claims made for Vapi/Retell — schema-valid, NOT live-deployed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from voice_agent.settings import KNOWN_DEPARTMENTS

PROVIDERS = Path(__file__).resolve().parents[1] / "providers"
CORE_TOOLS = {"check_availability", "book_slot", "route_call"}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_vapi_assistant_schema():
    cfg = _load(PROVIDERS / "vapi" / "assistant.json")
    assert cfg["model"]["provider"] and cfg["model"]["model"]
    assert cfg["model"]["messages"][0]["role"] == "system"
    names = {t["function"]["name"] for t in cfg["model"]["tools"]}
    assert names == CORE_TOOLS
    assert "voice" in cfg and "transcriber" in cfg


def test_retell_response_engine_schema():
    cfg = _load(PROVIDERS / "retell" / "response-engine.json")
    names = {t["name"] for t in cfg["general_tools"]}
    assert names == CORE_TOOLS
    assert cfg["model"]


def test_retell_agent_attaches_response_engine():
    cfg = _load(PROVIDERS / "retell" / "agent.json")
    assert cfg["response_engine"]["type"] == "retell-llm"
    assert "llm_id" in cfg["response_engine"]


@pytest.mark.parametrize("dept", KNOWN_DEPARTMENTS)
def test_department_enums_present_in_configs(dept):
    vapi = (PROVIDERS / "vapi" / "assistant.json").read_text(encoding="utf-8")
    retell = (PROVIDERS / "retell" / "response-engine.json").read_text(encoding="utf-8")
    assert dept in vapi and dept in retell
