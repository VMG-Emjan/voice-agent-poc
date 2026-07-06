"""Re-verify committed evidence: recompute hashes and compare to checksums.sha256.

    python scripts/verify_artifacts.py artifacts/level-a/booking

Exit code 0 = all artifacts match their recorded hashes (not edited after generation).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence import sha256_file  # noqa: E402


def verify_dir(d: Path) -> bool:
    checks = d / "checksums.sha256"
    if not checks.exists():
        print(f"[skip] no checksums.sha256 in {d}")
        return True
    ok = True
    for line in checks.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, name = line.split("  ", 1)
        target = d / name
        if not target.exists():
            print(f"[MISSING] {target}")
            ok = False
            continue
        actual = sha256_file(target)
        status = "OK" if actual == expected else "MISMATCH"
        if actual != expected:
            ok = False
        print(f"[{status}] {name}")
    return ok


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    roots = [Path(a) for a in argv] or [Path("artifacts")]
    all_ok = True
    for root in roots:
        for checks in root.rglob("checksums.sha256"):
            print(f"== {checks.parent} ==")
            all_ok &= verify_dir(checks.parent)
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
