"""Local text-to-speech via Piper (CPU, offline).

Two entry points depending on how piper-tts is installed:
- Python API (piper.PiperVoice) when the wheel exposes it, or
- the `piper` CLI as a subprocess fallback.
Both produce a real .wav; nothing here fabricates audio.
"""

from __future__ import annotations

import shutil
import subprocess
import wave
from pathlib import Path


class LocalTTS:
    def __init__(self, voice_model: str | Path):
        self.voice_model = Path(voice_model)

    def synthesize(self, text: str, out_wav: str | Path) -> Path:
        out = Path(out_wav)
        out.parent.mkdir(parents=True, exist_ok=True)
        try:
            return self._via_python_api(text, out)
        except ImportError:
            return self._via_cli(text, out)

    def _via_python_api(self, text: str, out: Path) -> Path:
        from piper import PiperVoice  # type: ignore

        # Cache the loaded voice across calls (model load is expensive).
        if getattr(self, "_voice", None) is None:
            self._voice = PiperVoice.load(str(self.voice_model))
        with wave.open(str(out), "wb") as wf:
            self._voice.synthesize_wav(text, wf)
        return out

    def _via_cli(self, text: str, out: Path) -> Path:
        exe = shutil.which("piper")
        if not exe:
            raise RuntimeError(
                "Piper not available: install the 'voice' extra (pip install '.[voice]') "
                "or put the `piper` binary on PATH, and download a voice .onnx model."
            )
        subprocess.run(
            [exe, "--model", str(self.voice_model), "--output_file", str(out)],
            input=text.encode("utf-8"),
            check=True,
        )
        return out
