"""
DIR-AI — Directory Intelligence CLI Node
Entry point invoked by the `dir-ai` console script.
"""

from dir_ai.ui.boot import run_boot_sequence
from dir_ai.controller.core import start_session


def main():
    run_boot_sequence()
    start_session()


if __name__ == "__main__":
    main()

