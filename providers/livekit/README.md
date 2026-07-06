# LiveKit provider (primary live path, opt-in)

`agent.py` runs a LiveKit `AgentSession` worker that reuses the verified core tools
(`src/voice_agent/tools.py`) for appointment booking + call routing, with
**VAD-based barge-in** for a fully local $0 stack.

**Status: UNVERIFIED in this repo.** A live room needs a LiveKit server, a microphone
client, and plugin models — none exercised in CI. What *is* verified is:
- the deterministic core (46 tests), and
- the Level-B **synthetic-audio** pipeline (real faster-whisper STT + Piper TTS →
  booking), see `../../artifacts/level-b/`.

This file is the opt-in path to close the remaining **live microphone + barge-in**
gap on your own machine.

## Run (opt-in)
```bash
pip install "livekit-agents[silero]" livekit-plugins-openai
cp providers/livekit/.env.example .env   # set LIVEKIT_URL / API key / secret
python providers/livekit/agent.py dev
```
Then connect a mic client (LiveKit Agents Playground or a token-authed web room).

Pin versions to the current docs before running:
<https://docs.livekit.io/agents/> · turns & interruptions:
<https://docs.livekit.io/agents/logic/turns/>
