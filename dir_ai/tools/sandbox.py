"""Deprecated shim: use :mod:`dir_ai.sandbox` directly.

Kept so the transitional CLI tools keep working until CP2 rebuilds them.
"""

from __future__ import annotations

from pathlib import Path

from dir_ai.sandbox import SandboxPolicy, default_policy, get_base_dir, safe_path

_POLICY: SandboxPolicy = default_policy()
BASE_DIR: Path = _POLICY.root

__all__ = ["BASE_DIR", "SandboxPolicy", "get_base_dir", "safe_path"]
