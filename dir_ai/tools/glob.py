"""glob: bounded path-pattern matching inside the sandbox."""

from __future__ import annotations

from pathlib import PurePosixPath, PureWindowsPath

from dir_ai.results import ErrorCode, ToolResult
from dir_ai.sandbox import SandboxError, SandboxPolicy
from dir_ai.tools.common import is_visible, load_gitignore

MAX_RESULTS = 1000


def glob_paths(
    policy: SandboxPolicy,
    pattern: str,
    path: str = ".",
    max_results: int = 200,
) -> ToolResult:
    if not pattern or "\x00" in pattern:
        return ToolResult.failure(ErrorCode.INVALID_ARGUMENT, "pattern must not be empty.")
    if max_results < 1 or max_results > MAX_RESULTS:
        return ToolResult.failure(
            ErrorCode.INVALID_ARGUMENT, f"max_results must be between 1 and {MAX_RESULTS}."
        )

    windows = PureWindowsPath(pattern)
    posix = PurePosixPath(pattern)
    if windows.drive or pattern.startswith(("/", "\\")) or ".." in posix.parts:
        return ToolResult.failure(
            ErrorCode.INVALID_ARGUMENT, "pattern must be relative and must not traverse parents."
        )

    try:
        base = policy.resolve(path, operation="glob")
    except SandboxError as exc:
        return ToolResult.failure(ErrorCode.DENIED, str(exc))

    if not policy.exists(base):
        return ToolResult.failure(ErrorCode.NOT_FOUND, f"Path not found: {path}")
    if not policy.is_dir(base):
        return ToolResult.failure(ErrorCode.NOT_A_DIRECTORY, f"Not a directory: {path}")

    spec = load_gitignore(policy)
    matches = [
        match for match in policy.glob_paths(base, pattern) if is_visible(policy, spec, match)
    ]
    truncated = len(matches) > max_results
    rendered = [policy.relative(match).as_posix() for match in matches[:max_results]]

    if not rendered:
        return ToolResult.success("No matches.")
    return ToolResult.success("\n".join(rendered), truncated=truncated)
