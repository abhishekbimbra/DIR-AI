"""write_file: typed content writes through the sandbox."""

from __future__ import annotations

from dir_ai.results import ErrorCode, ToolResult
from dir_ai.sandbox import SandboxError, SandboxPolicy


def write_file(policy: SandboxPolicy, filename: str, content: str) -> ToolResult:
    try:
        path = policy.resolve(filename, operation="write")
    except SandboxError as exc:
        return ToolResult.failure(ErrorCode.DENIED, str(exc))

    if policy.exists(path) and policy.is_dir(path):
        return ToolResult.failure(ErrorCode.IS_A_DIRECTORY, f"Is a directory: {filename}")

    try:
        written = policy.write_text(path, content)
    except SandboxError as exc:
        return ToolResult.failure(ErrorCode.DENIED, str(exc))
    except OSError as exc:
        return ToolResult.failure(ErrorCode.IO_ERROR, f"Could not write {filename}: {exc}")

    return ToolResult.success(f"Wrote {written} bytes to {filename}")
