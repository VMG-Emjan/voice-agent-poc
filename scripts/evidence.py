"""Shared helpers for producing REAL, checkable evidence artifacts.

Transcripts/logs are always written by an actual run — never hand-authored. Every
artifact set carries run-metadata.json (git SHA, command, components) and a
checksums.sha256 so `verify_artifacts.py` can confirm nothing was edited afterward.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def git_sha() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT,
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "UNKNOWN (no git)"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def write_checksums(out_dir: Path, files: list[Path]) -> Path:
    lines = [f"{sha256_file(f)}  {f.relative_to(out_dir).as_posix()}" for f in files if f.exists()]
    target = out_dir / "checksums.sha256"
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def write_metadata(out_dir: Path, level: str, mode: str, command: list[str],
                   components: dict, extra: dict | None = None) -> Path:
    meta = {
        "level": level,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_sha(),
        "command": " ".join(command),
        "python": sys.version.split()[0],
        "nlu_mode": mode,
        "components": components,
        "hand_edited_after_generation": False,
        **(extra or {}),
    }
    target = out_dir / "run-metadata.json"
    target.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    return target
