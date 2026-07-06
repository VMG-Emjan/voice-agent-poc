"""Level-B evidence: a REAL local voice pipeline over synthetic audio.

For each scripted user turn:
  text --(Piper TTS)--> input .wav --(faster-whisper STT)--> recognized text
       --> DialogManager --> bot text --(Piper TTS)--> reply .wav

This proves the STT -> NLU -> dialog -> tool -> TTS chain actually runs end to end.
It is HONEST about scope:
  * The input audio is SYNTHETIC (Piper), not a human microphone -> labeled synthetic.
  * Microphone capture + VAD barge-in + a live LiveKit room are NOT exercised here
    and remain UNVERIFIED (see providers/livekit/ for the opt-in live path).

    pip install ".[voice]"
    python scripts/run_voice_demo.py --record artifacts/level-b
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from evidence import REPO_ROOT, write_checksums, write_metadata  # noqa: E402

from voice_agent.agent import build_agent  # noqa: E402
from voice_agent.logging import EventLog  # noqa: E402
from voice_agent.providers.local_stt import LocalSTT  # noqa: E402
from voice_agent.providers.local_tts import LocalTTS  # noqa: E402
from voice_agent.settings import Settings  # noqa: E402
from voice_agent.state import TERMINAL  # noqa: E402

FIXED_NOW = datetime(2026, 7, 6, 10, 0, 0)

# Scripted user turns spoken (via TTS) into the pipeline.
# Phrasing chosen so synthetic TTS -> STT round-trips cleanly (spoken "15:00" is
# transcribed by Whisper as "$1500"; "3 PM" round-trips reliably). This is a known
# limitation of number formatting through TTS+STT, noted in the README.
TURNS = [
    "I would like to book an appointment",
    "My name is John Smith",
    "on 2026-07-12",
    "at 3 PM",
    "yes",
]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Record a Level-B synthetic-audio voice pipeline run.")
    p.add_argument("--record", default="artifacts/level-b")
    p.add_argument("--whisper", default=None, help="faster-whisper model size (default from env).")
    args = p.parse_args(argv)

    settings = Settings.from_env()
    whisper_size = args.whisper or settings.whisper_model
    voice_model = _resolve_voice_model(settings)

    out_dir = (REPO_ROOT / args.record).resolve()
    (out_dir / "audio").mkdir(parents=True, exist_ok=True)
    work = out_dir / "work"
    work.mkdir(exist_ok=True)
    import shutil

    shutil.copy(REPO_ROOT / "data" / "calendar.example.json", work / "calendar.example.json")
    (work / "appointments.json").unlink(missing_ok=True)

    stt = LocalSTT(model_size=whisper_size)
    tts = LocalTTS(voice_model)
    log = EventLog()
    agent = build_agent(nlu_mode="deterministic", data_dir=work,
                        now_provider=lambda: FIXED_NOW, log=log)

    transcript = ["# Level-B transcript — synthetic-audio voice pipeline", "",
                  f"- STT: faster-whisper:{whisper_size}", f"- TTS: piper ({voice_model.name})",
                  "- Input audio: SYNTHETIC (Piper). Not a human microphone.", ""]

    for i, turn in enumerate(TURNS):
        in_wav = out_dir / "audio" / f"turn{i:02d}_user.wav"
        tts.synthesize(turn, in_wav)                      # real TTS -> input audio
        rec = stt.transcribe(in_wav, language="en")       # real STT
        recognized = rec["text"]
        log.emit("stt", turn=i, expected=turn, recognized=recognized, model=rec["model"])

        reply = agent.handle(recognized)
        out_wav = out_dir / "audio" / f"turn{i:02d}_bot.wav"
        tts.synthesize(reply.text, out_wav)               # real TTS -> reply audio
        log.emit("tts", turn=i, text=reply.text, wav=out_wav.name)

        transcript += [
            f"**spoken>** {turn}",
            f"**heard (STT)>** {recognized}",
            f"**bot>** {reply.text}",
            "",
        ]
        if reply.state in TERMINAL:
            transcript.append(f"_(final state: {reply.state.value})_")
            break

    transcript_path = out_dir / "transcript.md"
    transcript_path.write_text("\n".join(transcript) + "\n", encoding="utf-8")
    session_path = out_dir / "session.jsonl"
    session_path.write_text(log.to_jsonl() + "\n", encoding="utf-8")

    meta_path = write_metadata(
        out_dir, level="B", mode="deterministic",
        command=["python", "scripts/run_voice_demo.py", "--record", args.record],
        components={
            "stt": f"faster-whisper:{whisper_size}",
            "tts": f"piper:{voice_model.name}",
            "nlu": "deterministic (rule-based, offline)",
        },
        extra={
            "input_audio": "synthetic (Piper TTS)",
            "human_microphone": False,
            "barge_in_vad": "UNVERIFIED (not exercised in this run)",
            "live_livekit_room": "UNVERIFIED (see providers/livekit/)",
            "fixed_clock": FIXED_NOW.isoformat(),
        },
    )
    # Hash the text artifacts + every generated wav.
    wavs = sorted((out_dir / "audio").glob("*.wav"))
    write_checksums(out_dir, [transcript_path, session_path, meta_path, *wavs])
    print(f"[level-b] wrote transcript + {len(wavs)} wav files to {out_dir}")
    return 0


def _resolve_voice_model(settings: Settings) -> Path:
    candidate = Path(settings.piper_voice_model)
    if not candidate.is_absolute():
        candidate = REPO_ROOT / candidate
    if not candidate.exists():
        # Fall back to any .onnx under models/.
        found = sorted((REPO_ROOT / "models").glob("*.onnx"))
        if found:
            return found[0]
        raise SystemExit(
            f"Piper voice model not found at {candidate}. Download one into models/ "
            "(e.g. en_US-amy-medium.onnx + .onnx.json) and set PIPER_VOICE_MODEL."
        )
    return candidate


if __name__ == "__main__":
    sys.exit(main())
