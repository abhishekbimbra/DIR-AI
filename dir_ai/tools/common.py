"""Shared helpers for tools: gitignore matching and visibility."""

from __future__ import annotations

from pathlib import Path

from pathspec import PathSpec

from dir_ai.sandbox import SandboxError, SandboxPolicy


def load_gitignore(policy: SandboxPolicy) -> PathSpec:
    path = policy.root / ".gitignore"
    try:
        if policy.exists(path) and policy.is_file(path):
            return PathSpec.from_lines("gitignore", policy.read_text(path).splitlines())
    except (OSError, SandboxError):
        pass
    return PathSpec.from_lines("gitignore", [])


def is_visible(policy: SandboxPolicy, spec: PathSpec, path: Path) -> bool:
    """Denylisted and gitignored paths are never shown by list/grep/glob."""
    if policy.is_denied(path):
        return False
    try:
        relative = policy.relative(path).as_posix()
    except SandboxError:
        return False
    if spec.match_file(relative):
        return False
    return not (policy.is_dir(path) and spec.match_file(relative.rstrip("/") + "/"))
