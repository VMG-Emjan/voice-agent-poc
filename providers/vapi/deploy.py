"""Create a Vapi assistant from assistant.json.

    export VAPI_API_KEY=...        # your private key
    python providers/vapi/deploy.py

OPT-IN and OUT OF SCOPE for the $0 proof: this makes a real API call to Vapi and,
if you attach a phone number, can incur charges. It is provided as copy-deploy-ready
tooling, NOT run as part of the verified evidence. Needs `pip install httpx`.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

API = "https://api.vapi.ai/assistant"


def main() -> int:
    key = os.getenv("VAPI_API_KEY")
    if not key:
        print("Set VAPI_API_KEY first. Aborting (no request made).")
        return 2
    body = json.loads((Path(__file__).parent / "assistant.json").read_text(encoding="utf-8"))
    if "REPLACE_WITH_YOUR_VOICE_ID" in json.dumps(body):
        print("Replace the placeholder voiceId in assistant.json first.")
        return 2

    import httpx

    resp = httpx.post(API, headers={"Authorization": f"Bearer {key}"}, json=body, timeout=30)
    print(resp.status_code, resp.text[:500])
    return 0 if resp.is_success else 1


if __name__ == "__main__":
    sys.exit(main())
