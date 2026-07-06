# Vapi provider (opt-in)

Maps the same appointment-booking + call-routing agent onto [Vapi](https://vapi.ai).

**Status: UNVERIFIED.** The JSON here is schema-validated in CI (parse + required
keys) but has **not** been deployed to a live Vapi account in this repo. Deploying
requires a Vapi API key and — for real phone calls — a paid number.

## Files
- `assistant.json` — assistant config: OpenAI model, `check_availability` /
  `book_slot` / `route_call` function tools, Deepgram transcriber, 11labs voice.
  Replace `voiceId` with your own.
- `deploy.py` — `POST https://api.vapi.ai/assistant` from `assistant.json`.

## Deploy (opt-in, may incur cost)
```bash
pip install httpx
export VAPI_API_KEY=...            # your private key
# edit assistant.json -> set voiceId
python providers/vapi/deploy.py
```

Schema reference (verified 2026-07-06):
<https://docs.vapi.ai/api-reference/assistants/create> ·
web-call quickstart: <https://docs.vapi.ai/quickstart/web>

The tool names/parameters mirror `src/voice_agent/tools.py`, so a Vapi webhook can
delegate to the same core logic.
