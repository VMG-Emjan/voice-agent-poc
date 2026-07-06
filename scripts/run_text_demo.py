"""Level-A evidence: run a scripted text conversation through the real agent and
record the transcript + structured event log + metadata + checksums.

    python scripts/run_text_demo.py --scenario booking --record artifacts/level-a

Nothing here is hand-written: the transcript is exactly what the DialogManager
produced for the given turns.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from evidence import REPO_ROOT, write_checksums, write_metadata  # noqa: E402

from voice_agent.agent import build_agent  # noqa: E402
from voice_agent.logging import EventLog  # noqa: E402
from voice_agent.state import TERMINAL  # noqa: E402

# Fixed clock so the recorded run is reproducible.
FIXED_NOW = datetime(2026, 7, 6, 10, 0, 0)

SCENARIOS: dict[str, list[str]] = {
    "booking": [
        "Hi, I'd like to book an appointment",
        "My name is John Smith",
        "on 2026-07-12",
        "at 14:00",          # blocked -> agent offers alternatives
        "15:00",
        "yes",
    ],
    "routing": [
        "Can you transfer my call?",
        "billing",
    ],
    "correction": [
        "book an appointment, my name is Ada Lovelace, on 2026-07-12 at 15:00",
        "actually make it 16:00",
        "yes",
    ],
}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Record a Level-A text-demo evidence bundle.")
    p.add_argument("--scenario", choices=sorted(SCENARIOS), default="booking")
    p.add_argument("--record", default="artifacts/level-a")
    args = p.parse_args(argv)

    out_dir = (REPO_ROOT / args.record / args.scenario).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # Isolated work dir so the demo's appointments.json doesn't leak into the repo.
    work = out_dir / "work"
    work.mkdir(exist_ok=True)
    shutil.copy(REPO_ROOT / "data" / "calendar.example.json", work / "calendar.example.json")
    (work / "appointments.json").unlink(missing_ok=True)

    log = EventLog()
    agent = build_agent(nlu_mode="deterministic", data_dir=work,
                        now_provider=lambda: FIXED_NOW, log=log)

    transcript: list[str] = [f"# Level-A transcript — scenario: {args.scenario}", ""]
    for turn in SCENARIOS[args.scenario]:
        reply = agent.handle(turn)
        transcript.append(f"**you>** {turn}")
        transcript.append(f"**bot>** {reply.text}")
        transcript.append("")
        if reply.state in TERMINAL:
            transcript.append(f"_(final state: {reply.state.value})_")
            break

    transcript_path = out_dir / "transcript.md"
    transcript_path.write_text("\n".join(transcript) + "\n", encoding="utf-8")

    session_path = out_dir / "session.jsonl"
    session_path.write_text(log.to_jsonl() + "\n", encoding="utf-8")

    appts = work / "appointments.json"
    booking_result = appts.read_text(encoding="utf-8") if appts.exists() else "[]"
    (out_dir / "booking-result.json").write_text(booking_result, encoding="utf-8")

    meta_path = write_metadata(
        out_dir, level="A", mode="deterministic",
        command=["python", "scripts/run_text_demo.py", "--scenario", args.scenario],
        components={"nlu": "deterministic (rule-based, offline)"},
        extra={"scenario": args.scenario, "fixed_clock": FIXED_NOW.isoformat()},
    )
    files = [transcript_path, session_path, out_dir / "booking-result.json", meta_path]
    write_checksums(out_dir, files)

    print(f"[level-a] wrote {len(files) + 1} artifacts to {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
