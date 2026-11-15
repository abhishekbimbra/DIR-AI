"""Unified-diff previews for approval requests."""

from __future__ import annotations

import difflib
from dataclasses import dataclass

from dir_ai.sandbox import SandboxError, SandboxPolicy

DEFAULT_MAX_DIFF_CHARS = 20_000


@dataclass(frozen=True, slots=True)
class DiffPreview:
    text: str
    is_new: bool = False
    overwrite: bool = False
    noop: bool = False
    truncated: bool = False


def _render_diff(relative: str, old: str, new: str, *, is_new: bool, max_chars: int) -> DiffPreview:
    if old == new:
        return DiffPreview(text="", is_new=is_new, overwrite=not is_new, noop=True)

    from_label = "/dev/null" if is_new else f"a/{relative}"
    to_label = f"b/{relative}"
    lines = difflib.unified_diff(
        old.splitlines(keepends=True),
        new.splitlines(keepends=True),
        fromfile=from_label,
        tofile=to_label,
    )
    text = "".join(lines)
    truncated = False
    if len(text) > max_chars:
        cut = text.rfind("\n", 0, max_chars)
        if cut < 0:  # pragma: no cover - a single unbounded line
            cut = max_chars
        text = text[:cut] + f"\n... [diff truncated; {len(text)} characters total]\n"
        truncated = True
    return DiffPreview(
        text=text,
        is_new=is_new,
        overwrite=not is_new,
        noop=False,
        truncated=truncated,
    )


def preview_write(
    policy: SandboxPolicy,
    filename: str,
    content: str,
    *,
    max_chars: int = DEFAULT_MAX_DIFF_CHARS,
) -> DiffPreview:
    """Build a diff for creating or overwriting *filename*."""
    path = policy.resolve(filename, operation="write")
    relative = policy.relative(path).as_posix()
    if policy.exists(path):
        old = policy.read_text(path)
        return _render_diff(relative, old, content, is_new=False, max_chars=max_chars)
    return _render_diff(relative, "", content, is_new=True, max_chars=max_chars)


def preview_edit(
    policy: SandboxPolicy,
    filename: str,
    old: str,
    new: str,
    *,
    max_chars: int = DEFAULT_MAX_DIFF_CHARS,
) -> DiffPreview | None:
    """Build a diff for a valid single-match edit, or None if the edit is invalid."""
    if not old or old == new:
        return None
    try:
        path = policy.resolve(filename, operation="write")
    except SandboxError:
        return None
    if not policy.exists(path) or not policy.is_file(path):
        return None
    try:
        current = policy.read_bytes(path).decode("utf-8")
    except (SandboxError, OSError, UnicodeDecodeError):
        return None
    if current.count(old) != 1:
        return None
    relative = policy.relative(path).as_posix()
    return _render_diff(
        relative, current, current.replace(old, new, 1), is_new=False, max_chars=max_chars
    )
