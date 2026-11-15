"""
DIR-AI — boot.py
UI-only cinematic startup sequence.
Fixed: init steps now centered, responsive to terminal width.
"""

import time
import random
import os
import pyfiglet
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from rich.rule import Rule
from rich.table import Table
from rich import box

console = Console()

VERSION   = "v0.1.0"
BUILD_TAG = "COGNITIVE ENGINE  ·  GEMINI BACKEND  ·  SANDBOX MODE"

INIT_STEPS = [
    ("Initializing Cognitive Core",  0.45),
    ("Loading Tool Registry",        0.30),
    ("Connecting LLM Backend",       0.55),
    ("Enabling Sandbox Mode",        0.30),
    ("Activating Planning Engine",   0.40),
    ("Calibrating ReAct Loop",       0.25),
]

LINE_GRADIENT = [
    (0,   255, 255),
    (0,   210, 255),
    (0,   170, 255),
    (50,  130, 255),
    (120,  80, 255),
    (180,  60, 240),
    (210,  40, 220),
    (230,  20, 200),
]

GLITCH_CHARS = list("|/-+<>#@%^&*=~!:;")


def _glitch_block(lines: list) -> Text:
    result = Text()
    for line in lines:
        glitched = "".join(
            random.choice(GLITCH_CHARS) if ch != " " else " "
            for ch in line
        )
        result.append(glitched + "\n", style="rgb(60,60,90)")
    return result


def _gradient_block(lines: list) -> Text:
    result = Text()
    for i, line in enumerate(lines):
        r, g, b = LINE_GRADIENT[i % len(LINE_GRADIENT)]
        result.append(line + "\n", style=f"bold rgb({r},{g},{b})")
    return result


def _render_logo():
    raw   = pyfiglet.figlet_format("DIR-AI", font="doom")
    lines = raw.splitlines()

    console.print()

    with Live(
        console=console,
        refresh_per_second=30,
        transient=False,
        vertical_overflow="visible",
    ) as live:
        for _ in range(5):
            live.update(Align.center(_glitch_block(lines)))
            time.sleep(0.04)
        live.update(Align.center(_gradient_block(lines)))
        time.sleep(0.35)

    console.print()


def _render_tagline():
    line = Text()
    line.append(f" {VERSION} ", style="bold black on rgb(0,210,255)")
    line.append("    ")
    line.append(BUILD_TAG, style="dim rgb(0,180,220)")
    console.print(Align.center(line))
    console.print()


def _make_step_text(label: str, state: str) -> Text:
    """
    Build a single centered step line.
    Fixed width block so centering is stable across LOADING → READY transition.
    """
    t = Text()
    t.append("◈  ", style="rgb(0,210,255)")
    t.append(f"{label:<40}", style="white" if state == "ready" else "dim white")
    if state == "loading":
        t.append("  [ LOADING ]", style="dim yellow")
    else:
        t.append("  [ ", style="dim rgb(0,255,150)")
        t.append("✓ READY", style="bold rgb(0,255,150)")
        t.append(" ]", style="dim rgb(0,255,150)")
    return t


def _render_init_steps():
    console.print(Rule(
        title="[dim rgb(0,180,220)]· SYSTEM INITIALIZATION ·[/dim rgb(0,180,220)]",
        style="rgb(35,35,55)",
    ))
    console.print()

    for label, duration in INIT_STEPS:
        with Live(
            console=console,
            refresh_per_second=20,
            transient=False,
            vertical_overflow="visible",
        ) as live:
            # LOADING — centered
            live.update(Align.center(_make_step_text(label, "loading")))
            time.sleep(duration)
            # READY — centered, same width so no layout shift
            live.update(Align.center(_make_step_text(label, "ready")))

    console.print()


def _render_ready_banner():
    msg = Text(justify="center")
    msg.append("\n")
    msg.append("  ✦  ", style="rgb(0,255,150)")
    msg.append("ALL SYSTEMS OPERATIONAL", style="bold white")
    msg.append("  —  ", style="dim rgb(0,210,255)")
    msg.append("DIR-AI IS READY", style="bold rgb(0,210,255)")
    msg.append("  ✦  ", style="rgb(0,255,150)")
    msg.append("\n")

    console.print(Panel(
        Align.center(msg),
        border_style="rgb(0,180,220)",
        box=box.DOUBLE_EDGE,
        padding=(0, 4),
    ))
    console.print()


def _render_status_bar():
    width = console.width or 80
    cwd   = os.path.basename(os.getcwd()) or "~"

    table = Table(
        box=None,
        show_header=False,
        show_edge=False,
        padding=(0, 2),
        expand=True,
        width=max(width - 4, 40),
    )
    table.add_column(justify="left",   no_wrap=True, ratio=2)
    table.add_column(justify="center", no_wrap=True, ratio=2)
    table.add_column(justify="right",  no_wrap=True, ratio=2)

    left = Text()
    left.append(f"~/{cwd}", style="bold white")
    left.append("  (sandbox active)", style="rgb(0,200,255)")

    center = Text()
    center.append("list", style="rgb(0,200,255)")
    center.append("  ·  ", style="dim white")
    center.append("read", style="rgb(0,200,255)")
    center.append("  ·  ", style="dim white")
    center.append("write", style="rgb(0,200,255)")

    right = Text()
    right.append("gemini-2.5-flash", style="bold rgb(0,200,255)")
    right.append("  (ready)", style="dim white")

    table.add_row(left, center, right)

    console.print(Panel(
        table,
        border_style="rgb(35,35,55)",
        box=box.ROUNDED,
        padding=(0, 1),
    ))
    console.print()


def run_boot_sequence():
    console.clear()
    console.print()
    _render_logo()
    _render_tagline()
    _render_init_steps()
    _render_ready_banner()
    _render_status_bar()


if __name__ == "__main__":
    run_boot_sequence()