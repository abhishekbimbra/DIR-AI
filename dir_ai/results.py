"""Uniform result type returned by every tool."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum


class ErrorCode(StrEnum):
    NOT_FOUND = "not_found"
    NOT_A_FILE = "not_a_file"
    NOT_A_DIRECTORY = "not_a_directory"
    IS_A_DIRECTORY = "is_a_directory"
    IS_A_FILE = "is_a_file"
    DENIED = "denied"
    TOO_LARGE = "too_large"
    BINARY = "binary"
    INVALID_ARGUMENT = "invalid_argument"
    NO_MATCH = "no_match"
    AMBIGUOUS = "ambiguous"
    IO_ERROR = "io_error"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ToolResult:
    ok: bool
    output: str = ""
    error_code: ErrorCode | None = None
    truncated: bool = False

    @classmethod
    def success(cls, output: str, *, truncated: bool = False) -> ToolResult:
        return cls(ok=True, output=output, truncated=truncated)

    @classmethod
    def failure(cls, code: ErrorCode, message: str) -> ToolResult:
        return cls(ok=False, output=message, error_code=code)

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "output": self.output,
            "error_code": self.error_code.value if self.error_code else None,
            "truncated": self.truncated,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)
