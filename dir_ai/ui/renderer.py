"""
UI Layer — Renders agent reasoning steps and final answers.
"""

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

console = Console()


def print_thought(text: str):
    console.print(f"  [bold cyan]Thought:[/bold cyan] {text}")


def print_action(tool_name: str):
    console.print(f"  [bold yellow]Action:[/bold yellow]  [yellow]{tool_name}[/yellow]")


def print_observation(text: str):
    console.print(f"  [bold blue]Observation:[/bold blue] {text}")


def print_final_answer(text: str):
    console.print()
    console.print(Rule(style="green"))
    console.print(
        Panel(
            f"[bold white]{text}[/bold white]",
            title="[bold green]Final Answer[/bold green]",
            border_style="green",
            padding=(1, 2),
        )
    )
    console.print(Rule(style="green"))
    console.print()


def print_planning():
    console.print()
    console.print("  [bold magenta]Planning...[/bold magenta]")
    console.print()


def print_error(text: str):
    console.print(f"  [bold red]Error:[/bold red] {text}")
