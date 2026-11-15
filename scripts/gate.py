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
    1: 40,
    2: 55,
    3: 60,
    4: 65,
    5: 70,
    6: 75,
    7: 75,
    8: 75,
    9: 80,
}

# Checkpoint-specific modules that must hit 100% branch coverage.
STRICT_MODULES: dict[int, tuple[str, ...]] = {
    1: ("dir_ai.sandbox",),
    2: ("dir_ai.sandbox",),
    3: ("dir_ai.sandbox", "dir_ai.approval", "dir_ai.policy", "dir_ai.diff"),
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
        coverage_args = [f"--cov={module}" for module in strict]
        run(
            [
                PY,
                "-m",
                "pytest",
                "--cov-branch",
                *coverage_args,
                "--cov-report=term-missing",
                "--cov-fail-under=100",
                "tests/unit",
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
