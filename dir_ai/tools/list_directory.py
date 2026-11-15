"""list_directory: flat or recursive listing, gitignore and denylist aware."""

from __future__ import annotations

from dir_ai.results import ErrorCode, ToolResult
from dir_ai.sandbox import SandboxError, SandboxPolicy
from dir_ai.tools.common import is_visible, load_gitignore


def list_directory(
    policy: SandboxPolicy,
    path: str = ".",
    recursive: bool = False,
    max_entries: int = 500,
) -> ToolResult:
    if max_entries < 1:
        return ToolResult.failure(ErrorCode.INVALID_ARGUMENT, "max_entries must be positive.")
    try:
        base = policy.resolve(path, operation="list")
    except SandboxError as exc:
        return ToolResult.failure(ErrorCode.DENIED, str(exc))

    if not policy.exists(base):
        return ToolResult.failure(ErrorCode.NOT_FOUND, f"Path not found: {path}")
    if not policy.is_dir(base):
        return ToolResult.failure(ErrorCode.NOT_A_DIRECTORY, f"Not a directory: {path}")

    spec = load_gitignore(policy)
    entries = policy.walk(base) if recursive else policy.iter_dir(base)
    visible = [entry for entry in entries if is_visible(policy, spec, entry)]
    truncated = len(visible) > max_entries

    lines: list[str] = []
    for entry in visible[:max_entries]:
        label = policy.relative(entry).as_posix() if recursive else entry.name
        tag = "[DIR]" if policy.is_dir(entry) else "[FILE]"
        lines.append(f"{tag} {label}")

    return ToolResult.success("\n".join(lines) or "The directory is empty.", truncated=truncated)
