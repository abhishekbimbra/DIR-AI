"""DIR-AI command-line entry point.

Configuration is validated *before* the boot animation so failures are immediate
and readable.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from dir_ai import __version__
from dir_ai.config import PROVIDERS, ConfigError, Settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dir-ai",
        description="Local, sandboxed directory-intelligence coding agent.",
    )
    parser.add_argument("--provider", choices=PROVIDERS, help="Model provider to use.")
    parser.add_argument("--model", help="Provider model name.")
    parser.add_argument(
        "--fake-llm",
        action="store_true",
        help="Use the scripted fake model instead of a real provider.",
    )
    parser.add_argument("--no-boot", action="store_true", help="Skip the boot animation.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        settings = Settings.from_env(load_file=True).with_overrides(
            provider=args.provider, model=args.model
        )
    except ConfigError as exc:
        print(f"[DIR-AI] Configuration error:\n{exc}", file=sys.stderr)
        return 2

    if not args.no_boot:
        from dir_ai.ui.boot import run_boot_sequence

        run_boot_sequence(provider=settings.provider, model=settings.model)

    from dir_ai.controller.core import start_session

    start_session(settings)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
