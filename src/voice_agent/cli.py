"""Interactive text CLI for the deterministic / local-llm core.

    python -m voice_agent.cli --nlu deterministic
    python -m voice_agent.cli --nlu local-llm

Scripted (for reproducible evidence) via --script FILE (one user line per row).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .agent import build_agent
from .state import TERMINAL


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="voice-agent", description="Text voice-agent core.")
    parser.add_argument("--nlu", choices=["deterministic", "local-llm"], default="deterministic")
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--script", help="Read user turns from a file instead of stdin.")
    args = parser.parse_args(argv)

    agent = build_agent(nlu_mode=args.nlu, data_dir=args.data_dir)
    print(f"[voice-agent] nlu={args.nlu}. Try 'book an appointment' or 'transfer me'.")

    if args.script:
        lines = Path(args.script).read_text(encoding="utf-8").splitlines()
        return _run_turns(agent, (ln for ln in lines if ln.strip()), echo=True)
    return _run_turns(agent, _stdin_turns(), echo=False)


def _stdin_turns():
    try:
        while True:
            yield input("you> ")
    except (EOFError, KeyboardInterrupt):
        return


def _run_turns(agent, turns, echo: bool) -> int:
    for text in turns:
        if echo:
            print(f"you> {text}")
        reply = agent.handle(text)
        print(f"bot> {reply.text}")
        if reply.state in TERMINAL:
            # Reset so a scripted file can contain multiple conversations if desired.
            if reply.state.value in {"cancelled", "failed"}:
                break
            break
    return 0


if __name__ == "__main__":
    sys.exit(main())
