"""Create a Retell response engine (LLM) then an agent that attaches it.

    export RETELL_API_KEY=...
    python providers/retell/deploy.py

OPT-IN and OUT OF SCOPE for the $0 proof: real API calls to Retell; a published
agent + phone number can incur cost. Provided as copy-deploy-ready tooling, not run
as verified evidence. Needs `pip install httpx`.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

LLM_API = "https://api.retellai.com/create-retell-llm"
AGENT_API = "https://api.retellai.com/create-agent"


def main() -> int:
    key = os.getenv("RETELL_API_KEY")
    if not key:
        print("Set RETELL_API_KEY first. Aborting (no request made).")
        return 2

    import httpx

    here = Path(__file__).parent
    headers = {"Authorization": f"Bearer {key}"}

    llm_body = _strip_notes(json.loads((here / "response-engine.json").read_text("utf-8")))
    llm = httpx.post(LLM_API, headers=headers, json=llm_body, timeout=30)
    print("LLM:", llm.status_code, llm.text[:300])
    if not llm.is_success:
        return 1
    llm_id = llm.json().get("llm_id")

    agent_body = _strip_notes(json.loads((here / "agent.json").read_text("utf-8")))
    agent_body["response_engine"]["llm_id"] = llm_id  # wire step 1 -> step 2
    if "REPLACE_WITH_YOUR_RETELL_VOICE_ID" in json.dumps(agent_body):
        print("Set voice_id in agent.json first.")
        return 2
    agent = httpx.post(AGENT_API, headers=headers, json=agent_body, timeout=30)
    print("AGENT:", agent.status_code, agent.text[:300])
    return 0 if agent.is_success else 1


def _strip_notes(obj: dict) -> dict:
    return {k: v for k, v in obj.items() if not k.startswith("_")}


if __name__ == "__main__":
    sys.exit(main())
