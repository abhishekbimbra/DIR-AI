"""
Middleware Layer — Human approval gate for write operations.
"""

from rich.console import Console

console = Console()


def request_approval(action_description: str) -> bool:
    """
    Prompt the user to approve a potentially destructive action.
    Returns True if approved, False otherwise.
    """
    console.print(f"\n  [bold yellow]Approval Required:[/bold yellow] {action_description}")
    response = console.input("  Proceed? [bold](y/n)[/bold]: ").strip().lower()
    approved = response in {"y", "yes"}
    if not approved:
        console.print("  [dim red]Action cancelled by user.[/dim red]\n")
    return approved
