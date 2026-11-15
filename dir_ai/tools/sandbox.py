"""
Tool Layer — Sandbox path resolution and validation.
All file operations must pass through here.
"""

import os
from pathlib import Path

# The directory where dir-ai was launched
BASE_DIR = Path(os.getcwd()).resolve()


def safe_path(filename: str) -> Path:
    """
    Resolve a filename relative to BASE_DIR.
    Raises ValueError if the resolved path escapes the sandbox.
    """
    resolved = (BASE_DIR / filename).resolve()
    if not str(resolved).startswith(str(BASE_DIR)):
        raise ValueError(f"Access denied: '{filename}' is outside the working directory.")
    return resolved
