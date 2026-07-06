"""LiveKit Agents worker — the PRIMARY provider path for a live voice room.

This wires the SAME core tools (src/voice_agent/tools.py) into a LiveKit
`AgentSession`, so a real-time room gets appointment booking + call routing with
VAD-based barge-in.

STATUS: UNVERIFIED in this repo. Running it needs a LiveKit server (local dev or
Cloud), a microphone client, and the plugin models. The deterministic core and the
Level-B synthetic-audio pipeline are what is actually verified here; this file is the
opt-in live path. Pin plugin versions per the current docs before running:
<https://docs.livekit.io/agents/> · turns/interruptions:
<https://docs.livekit.io/agents/logic/turns/>

Run (opt-in):
    pip install "livekit-agents[silero]" livekit-plugins-openai
    # set LIVEKIT_URL / LIVEKIT_API_KEY / LIVEKIT_API_SECRET in .env
    python providers/livekit/agent.py dev
"""

from __future__ import annotations

import sys
from pathlib import Path

# Reuse the verified core.
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from voice_agent.settings import KNOWN_DEPARTMENTS  # noqa: E402
from voice_agent.storage import AppointmentStore  # noqa: E402
from voice_agent.tools import Tools  # noqa: E402

_tools = Tools(REPO_ROOT / "data" / "calendar.example.json",
               AppointmentStore(REPO_ROOT / "data" / "appointments.json"))

INSTRUCTIONS = (
    "You are a phone receptionist. Book appointments (collect name, date YYYY-MM-DD, "
    "time HH:MM; confirm before booking) and route calls to "
    f"{', '.join(KNOWN_DEPARTMENTS)}. Never book without explicit confirmation. "
    "Always call the tools; never invent availability."
)


def _build_entrypoint():
    """Import LiveKit lazily so this module is importable without the extra installed."""
    from livekit.agents import Agent, AgentSession, RunContext, function_tool
    from livekit.plugins import openai, silero

    class ReceptionAgent(Agent):
        def __init__(self) -> None:
            super().__init__(instructions=INSTRUCTIONS)

        @function_tool
        async def check_availability(self, ctx: RunContext, date: str) -> str:
            return _tools.check_availability(date).message

        @function_tool
        async def book_slot(self, ctx: RunContext, name: str, date: str, time: str) -> str:
            return _tools.book_slot(name, date, time).message

        @function_tool
        async def route_call(self, ctx: RunContext, department: str) -> str:
            return _tools.route_call(department).message

    async def entrypoint(ctx) -> None:
        await ctx.connect()
        session = AgentSession(
            vad=silero.VAD.load(),                 # VAD-based barge-in ($0 local)
            # For a fully local $0 stack, point STT/TTS at local plugins or an
            # OpenAI-compatible localhost endpoint. Defaults below assume such a base_url.
            stt=openai.STT(base_url="http://localhost:8000/v1", api_key="local"),
            llm=openai.LLM(base_url="http://localhost:11434/v1", api_key="ollama",
                           model="llama3.2:1b"),
            tts=openai.TTS(base_url="http://localhost:8000/v1", api_key="local"),
        )
        await session.start(agent=ReceptionAgent(), room=ctx.room)
        await session.generate_reply(
            instructions="Greet the caller and offer to book or transfer."
        )

    return entrypoint


def main() -> None:
    from livekit.agents import WorkerOptions, cli

    cli.run_app(WorkerOptions(entrypoint_fnc=_build_entrypoint()))


if __name__ == "__main__":
    main()
