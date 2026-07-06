"""Local speech-to-text via faster-whisper (CPU, offline).

Used by scripts/run_voice_demo.py for the Level-B pipeline. Heavy dependency, so it
is imported lazily and lives behind the 'voice' extra — the deterministic core and CI
never touch it.
"""

from __future__ import annotations

from pathlib import Path


class LocalSTT:
    def __init__(self, model_size: str = "base", device: str = "cpu",
                 compute_type: str = "int8"):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model = None

    def _ensure(self):
        if self._model is None:
            from faster_whisper import WhisperModel  # lazy: only when voice extra installed

            self._model = WhisperModel(
                self.model_size, device=self.device, compute_type=self.compute_type
            )
        return self._model

    def transcribe(self, wav_path: str | Path, language: str | None = None) -> dict:
        """Return {'text': str, 'segments': [...], 'language': str}. Real STT, no mocking."""
        model = self._ensure()
        segments, info = model.transcribe(str(wav_path), language=language, vad_filter=True)
        seg_list = [
            {"start": round(s.start, 3), "end": round(s.end, 3), "text": s.text.strip()}
            for s in segments
        ]
        return {
            "text": " ".join(s["text"] for s in seg_list).strip(),
            "segments": seg_list,
            "language": info.language,
            "model": f"faster-whisper:{self.model_size}",
        }
