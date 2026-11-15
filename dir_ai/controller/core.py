"""Controller layer — interactive REPL session."""

from __future__ import annotations

from rich.console import Console

from dir_ai.config import Settings
from dir_ai.ui.renderer import print_error

console = Console()

PROMPT = "[bold bright_blue]dir-ai[/bold bright_blue] [dim white]>[/dim white] "
EXIT_COMMANDS = {"exit", "quit", "q", "bye"}


def start_session(settings: Settings) -> None:
    from dir_ai.agent.runner import run_agent

    console.print("  Type your request and press Enter. Type [bold]exit[/bold] to quit.\n")

    while True:
        try:
            user_input = console.input(PROMPT).strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n\n  [dim]Session terminated.[/dim]\n")
            break

        if not user_input:
            continue

        if user_input.lower() in EXIT_COMMANDS:
            console.print("\n  [dim]Shutting down DIR-AI. Goodbye.[/dim]\n")
            break

        try:
            run_agent(user_input, settings)
        except Exception as exc:  # noqa: BLE001 - REPL must survive tool failures
            print_error(f"Agent encountered an error: {exc}")
