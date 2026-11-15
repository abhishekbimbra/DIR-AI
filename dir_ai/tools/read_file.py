"""read_file: paged text reads with binary and size protection."""

from __future__ import annotations

from dir_ai.results import ErrorCode, ToolResult
from dir_ai.sandbox import FileTooLargeError, SandboxError, SandboxPolicy

MAX_LIMIT = 2000
BINARY_SNIFF_BYTES = 8192


def read_file(
    policy: SandboxPolicy,
    filename: str,
    offset: int = 0,
    limit: int = 200,
) -> ToolResult:
    if offset < 0:
        return ToolResult.failure(ErrorCode.INVALID_ARGUMENT, "offset must be zero or greater.")
    if limit < 1 or limit > MAX_LIMIT:
        return ToolResult.failure(
            ErrorCode.INVALID_ARGUMENT, f"limit must be between 1 and {MAX_LIMIT}."
        )

    try:
        path = policy.resolve(filename, operation="read")
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

    if b"\x00" in data[:BINARY_SNIFF_BYTES]:
        return ToolResult.failure(ErrorCode.BINARY, f"Binary file: {filename}")

    text = data.decode("utf-8", errors="replace")
    lines = text.splitlines(keepends=True)
    total = len(lines)
    selected = lines[offset : offset + limit]
    truncated = offset + limit < total

    header = f"[{filename}: lines {offset + 1}-{offset + len(selected)} of {total}]"
    body = "".join(selected)
    return ToolResult.success(f"{header}\n{body}" if total else "", truncated=truncated)
