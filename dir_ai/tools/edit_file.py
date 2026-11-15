"""edit_file: exact, single-match replacement."""

from __future__ import annotations

from dir_ai.results import ErrorCode, ToolResult
from dir_ai.sandbox import FileTooLargeError, SandboxError, SandboxPolicy


def edit_file(policy: SandboxPolicy, filename: str, old: str, new: str) -> ToolResult:
    if not old:
        return ToolResult.failure(ErrorCode.INVALID_ARGUMENT, "old text must not be empty.")
    if old == new:
        return ToolResult.failure(ErrorCode.INVALID_ARGUMENT, "old and new text are identical.")

    try:
        path = policy.resolve(filename, operation="write")
    except SandboxError as exc:
        return ToolResult.failure(ErrorCode.DENIED, str(exc))

    if not policy.exists(path):
        return ToolResult.failure(ErrorCode.NOT_FOUND, f"File not found: {filename}")
    if not policy.is_file(path):
        return ToolResult.failure(ErrorCode.NOT_A_FILE, f"Not a file: {filename}")

    try:
        data = policy.read_bytes(path)
    except FileTooLargeError as exc:
        return ToolResult.failure(ErrorCode.TOO_LARGE, str(exc))
    except OSError as exc:
        return ToolResult.failure(ErrorCode.IO_ERROR, f"Could not read {filename}: {exc}")

    if b"\x00" in data[:8192]:
        return ToolResult.failure(ErrorCode.BINARY, f"Binary file: {filename}")

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return ToolResult.failure(ErrorCode.BINARY, f"File is not valid UTF-8: {filename}")

    matches = text.count(old)
    if matches == 0:
        return ToolResult.failure(ErrorCode.NO_MATCH, f"old text was not found in {filename}.")
    if matches > 1:
        return ToolResult.failure(
            ErrorCode.AMBIGUOUS,
            f"old text appears {matches} times in {filename}; make it unique.",
        )

    updated = text.replace(old, new, 1)
    try:
        policy.write_text(path, updated)
    except SandboxError as exc:
        return ToolResult.failure(ErrorCode.DENIED, str(exc))
    except OSError as exc:
        return ToolResult.failure(ErrorCode.IO_ERROR, f"Could not write {filename}: {exc}")

    return ToolResult.success(f"Edited {filename}.")
