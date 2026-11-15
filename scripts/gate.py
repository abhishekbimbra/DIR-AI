#!/usr/bin/env python3
"""Checkpoint gate runner.

Usage:
    python scripts/gate.py 0            # run checks
    python scripts/gate.py 0 --tag      # run checks, then tag cp0-done

Checks are cumulative: every gate reruns every earlier test.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable

# Overall coverage floor per checkpoint. Raised as modules gain tests.
COVERAGE_FLOOR: dict[int, int] = {
    0: 25,
    1: 55,
    2: 70,
    3: 75,
    4: 80,
    5: 80,
    6: 80,
    7: 80,
    8: 80,
    9: 85,
}

# Checkpoint-specific modules that must hit 100% branch coverage.
STRICT_MODULES: dict[int, str] = {
    1: "dir_ai.sandbox",
}


def run(command: list[str]) -> None:
    print(f"\n$ {' '.join(command)}", flush=True)
    result = subprocess.run(command, cwd=ROOT, check=False)
    if result.returncode != 0:
        print(f"\nGATE FAILED: {' '.join(command)}", file=sys.stderr)
        raise SystemExit(result.returncode)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=int, choices=sorted(COVERAGE_FLOOR))
    parser.add_argument("--tag", action="store_true", help="Tag cpN-done after a pass")
    args = parser.parse_args()
    checkpoint = args.checkpoint

    run([PY, "-m", "ruff", "check", "."])
    run([PY, "-m", "ruff", "format", "--check", "."])
    run([PY, "-m", "mypy", "dir_ai"])

    pytest_command = [
        PY,
        "-m",
        "pytest",
        "--cov=dir_ai",
        "--cov-report=term-missing",
        f"--cov-fail-under={COVERAGE_FLOOR[checkpoint]}",
    ]
    run(pytest_command)

    strict = STRICT_MODULES.get(checkpoint)
    if strict:
        run(
            [
                PY,
                "-m",
                "pytest",
                "--cov-branch",
                f"--cov={strict}",
                "--cov-report=term-missing",
                "--cov-fail-under=100",
                f"tests/unit/test_{strict.rsplit('.', 1)[-1]}.py",
            ]
        )

    if args.tag:
        dirty = subprocess.run(
            ["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
        if dirty:
            print("\nRefusing to tag: working tree is not clean.\n" + dirty, file=sys.stderr)
            return 1
        tag = f"cp{checkpoint}-done"
        run(["git", "tag", "-a", tag, "-m", f"Backend checkpoint {checkpoint} passed"])

    print(f"\nCP{checkpoint} gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
