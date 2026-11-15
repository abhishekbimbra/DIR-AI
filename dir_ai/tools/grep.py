"""grep: bounded regex search over visible text files."""

from __future__ import annotations

import re

from dir_ai.results import ErrorCode, ToolResult
from dir_ai.sandbox import SandboxError, SandboxPolicy
from dir_ai.tools.common import is_visible, load_gitignore

MAX_RESULTS = 1000
MAX_PATTERN_LENGTH = 500


def grep(
    policy: SandboxPolicy,
    pattern: str,
    path: str = ".",
    max_results: int = 100,
    case_sensitive: bool = True,
) -> ToolResult:
    if not pattern or len(pattern) > MAX_PATTERN_LENGTH:
        return ToolResult.failure(
            ErrorCode.INVALID_ARGUMENT,
            f"pattern must be 1-{MAX_PATTERN_LENGTH} characters.",
        )
    if max_results < 1 or max_results > MAX_RESULTS:
        return ToolResult.failure(
            ErrorCode.INVALID_ARGUMENT, f"max_results must be between 1 and {MAX_RESULTS}."
        )
    try:
        expression = re.compile(pattern, 0 if case_sensitive else re.IGNORECASE)
    except re.error as exc:
        return ToolResult.failure(ErrorCode.INVALID_ARGUMENT, f"Invalid regex: {exc}")

    try:
        base = policy.resolve(path, operation="grep")
    except SandboxError as exc:
        return ToolResult.failure(ErrorCode.DENIED, str(exc))

    if not policy.exists(base):
        return ToolResult.failure(ErrorCode.NOT_FOUND, f"Path not found: {path}")
    if policy.is_file(base):
        candidates = [base]
    elif policy.is_dir(base):
        candidates = policy.walk(base)
    else:
        return ToolResult.failure(ErrorCode.NOT_A_DIRECTORY, f"Not a file or directory: {path}")

    spec = load_gitignore(policy)
    matches: list[str] = []
    truncated = False

    for entry in candidates:
        if len(matches) >= max_results:
            truncated = True
            break
        if not policy.is_file(entry) or not is_visible(policy, spec, entry):
            continue
        try:
            data = policy.read_bytes(entry)
        except (OSError, SandboxError):
            continue
        if b"\x00" in data[:8192]:
            continue
        relative = policy.relative(entry).as_posix()
        for number, line in enumerate(data.decode("utf-8", errors="replace").splitlines(), 1):
            if expression.search(line):
                matches.append(f"{relative}:{number}:{line}")
                if len(matches) >= max_results:
                    truncated = True
                    break

    if not matches:
        return ToolResult.success("No matches.")
    return ToolResult.success("\n".join(matches), truncated=truncated)
