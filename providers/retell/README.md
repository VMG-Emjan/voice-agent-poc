# Retell provider (opt-in)

Same agent on [Retell AI](https://retellai.com). Retell separates the **response
engine (LLM)** from the **agent** — you create the LLM first, then attach its
`llm_id` when creating the agent.

**Status: UNVERIFIED.** JSON is schema-validated in CI; not deployed to a live
account here. Deploy needs a Retell API key (and a number for real calls).

## Files
- `response-engine.json` — step 1: `create-retell-llm` body (prompt + custom tools).
- `agent.json` — step 2: `create-agent` body; put the returned `llm_id` here.
- `deploy.py` — runs both steps and wires `llm_id` automatically.

## Deploy (opt-in, may incur cost)
```bash
pip install httpx
export RETELL_API_KEY=...
# set voice_id in agent.json
python providers/retell/deploy.py
```

Schema reference (verified 2026-07-06):
agent API <https://docs.retellai.com/api-references/create-chat-agent> ·
web call <https://docs.retellai.com/deploy/web-call>
