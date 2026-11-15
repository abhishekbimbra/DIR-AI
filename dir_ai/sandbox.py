"""Sandbox: the single gate for all filesystem access.

Every path used by a tool must pass through :meth:`SandboxPolicy.resolve`.
The policy rejects absolute paths, parent traversal, symlink escapes, secret
files, VCS internals, and disallowed operations.
"""

from __future__ import annotations

import fnmatch
import os
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath

DEFAULT_DENY_GLOBS: tuple[str, ...] = (
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
    "*.p12",
    "*.pfx",
    "id_rsa*",
    "id_ed25519*",
    "id_ecdsa*",
    "*.kdbx",
)
DEFAULT_DENY_DIRS: tuple[str, ...] = (".git", ".ssh", ".aws", ".gnupg")
DEFAULT_OPERATIONS: frozenset[str] = frozenset({"read", "write", "list", "glob", "grep"})

MAX_FILE_SIZE = 2_000_000


class SandboxError(ValueError):
    """Base class for every sandbox rejection."""


class PathEscapeError(SandboxError):
    """The path is absolute, traverses out of the root, or is malformed."""


class DeniedPathError(SandboxError):
    """The path names a secret, VCS internal, or otherwise denied file."""


class OperationDeniedError(SandboxError):
    """The policy does not allow this operation."""


class FileTooLargeError(SandboxError):
    """The file exceeds the policy's size limit."""


@dataclass(frozen=True, slots=True)
class SandboxPolicy:
    """Root, denylist, size limit, and allowed operations for one session."""

    root: Path
    deny_globs: tuple[str, ...] = DEFAULT_DENY_GLOBS
    deny_dirs: tuple[str, ...] = DEFAULT_DENY_DIRS
    max_file_size: int = MAX_FILE_SIZE
    allowed_operations: frozenset[str] = DEFAULT_OPERATIONS

    def __post_init__(self) -> None:
        root = Path(self.root).expanduser()
        try:
            resolved = root.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise PathEscapeError(f"Sandbox root is not accessible: {root}") from exc
        if not resolved.is_dir():
            raise PathEscapeError(f"Sandbox root is not a directory: {resolved}")
        object.__setattr__(self, "root", resolved)
        if self.max_file_size < 1:
            raise SandboxError("max_file_size must be positive")
        unknown = set(self.allowed_operations) - DEFAULT_OPERATIONS
        if unknown:
            raise SandboxError(f"Unknown operations: {sorted(unknown)}")

    def resolve(self, candidate: str | os.PathLike[str], *, operation: str = "read") -> Path:
        """Resolve *candidate* inside the root or raise :class:`SandboxError`."""
        if operation not in self.allowed_operations:
            raise OperationDeniedError(f"Operation {operation!r} is not allowed.")

        raw = os.fspath(candidate)
        if not isinstance(raw, str):
            raise PathEscapeError("Path must be text.")
        if "\x00" in raw:
            raise PathEscapeError("Path contains a null byte.")
        if not raw.strip():
            raise PathEscapeError("Path is empty.")
        if len(raw) > 4096:
            raise PathEscapeError("Path is too long.")
        if any(len(part.encode("utf-8", "surrogatepass")) > 255 for part in raw.split("/")):
            raise PathEscapeError(f"Path component is too long: {raw[:40]!r}...")
        if self._looks_like_windows_absolute(raw):
            raise PathEscapeError(f"Absolute paths are not allowed: {raw!r}")

        try:
            relative = Path(raw)
        except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
            raise PathEscapeError(f"Invalid path: {raw!r}") from exc
        if relative.is_absolute():
            raise PathEscapeError(f"Absolute paths are not allowed: {raw!r}")

        try:
            resolved = (self.root / relative).resolve(strict=False)
        except (OSError, RuntimeError) as exc:  # pragma: no cover - defensive
            raise PathEscapeError(f"Path cannot be resolved: {raw!r}") from exc

        if not resolved.is_relative_to(self.root):
            raise PathEscapeError(f"Path escapes the sandbox: {raw!r}")

        self._check_denied(resolved)
        return resolved

    def relative(self, path: Path) -> Path:
        """Return *path* relative to the root, or raise."""
        try:
            return Path(path).resolve(strict=False).relative_to(self.root)
        except (ValueError, OSError, RuntimeError) as exc:
            raise PathEscapeError(f"Path is outside the sandbox: {path}") from exc

    def check_size(self, path: Path) -> None:
        """Reject files larger than the policy limit."""
        try:
            size = path.stat().st_size
        except OSError:
            return
        if size > self.max_file_size:
            raise FileTooLargeError(
                f"File is {size} bytes; the limit is {self.max_file_size} bytes."
            )

    def ensure_parent(self, path: Path) -> None:
        """Create missing parent directories inside the root."""
        parent = path.parent
        if not parent.resolve(strict=False).is_relative_to(self.root):
            raise PathEscapeError(f"Parent escapes the sandbox: {parent}")
        parent.mkdir(parents=True, exist_ok=True)

    # -- filesystem primitives -------------------------------------------------
    # These are the only raw I/O operations in the package. Tools must use them.

    def exists(self, path: Path) -> bool:
        return path.exists()

    def is_file(self, path: Path) -> bool:
        return path.is_file()

    def is_dir(self, path: Path) -> bool:
        return path.is_dir()

    def stat_size(self, path: Path) -> int:
        return path.stat().st_size

    def read_bytes(self, path: Path, *, max_bytes: int | None = None) -> bytes:
        limit = self.max_file_size if max_bytes is None else min(max_bytes, self.max_file_size)
        with path.open("rb") as handle:
            data = handle.read(limit + 1)
        if len(data) > limit:
            raise FileTooLargeError(f"File exceeds the {limit}-byte read limit.")
        return data

    def read_text(self, path: Path) -> str:
        return self.read_bytes(path).decode("utf-8", errors="replace")

    def write_text(self, path: Path, content: str) -> int:
        self.ensure_parent(path)
        data = content.encode("utf-8")
        path.write_bytes(data)
        return len(data)

    def iter_dir(self, path: Path) -> list[Path]:
        return sorted(path.iterdir(), key=lambda entry: entry.name.lower())

    def walk(self, path: Path) -> list[Path]:
        """Every descendant, sorted. Symlinked directories are not followed."""
        return sorted(path.rglob("*"), key=lambda entry: entry.as_posix().lower())

    def glob_paths(self, base: Path, pattern: str) -> list[Path]:
        results: list[Path] = []
        for match in sorted(base.glob(pattern), key=lambda entry: entry.as_posix().lower()):
            try:
                resolved = match.resolve(strict=False)
            except (OSError, RuntimeError):  # pragma: no cover - defensive
                continue
            if resolved.is_relative_to(self.root) and not self.is_denied(resolved):
                results.append(resolved)
        return results

    def is_denied(self, path: Path) -> bool:
        try:
            resolved = Path(path).resolve(strict=False)
            if not resolved.is_relative_to(self.root):
                return True
            self._check_denied(resolved)
        except (SandboxError, ValueError, OSError, RuntimeError):
            return True
        return False

    def _check_denied(self, resolved: Path) -> None:
        parts = resolved.relative_to(self.root).parts
        for part in parts:
            lowered = part.lower()
            if lowered in self.deny_dirs:
                raise DeniedPathError(f"Access to {part!r} is denied.")
            if any(fnmatch.fnmatch(lowered, pattern.lower()) for pattern in self.deny_globs):
                raise DeniedPathError(f"Access to {part!r} is denied.")

    @staticmethod
    def _looks_like_windows_absolute(raw: str) -> bool:
        # Reject drive-letter and UNC paths on every platform: a POSIX checkout
        # must never treat them as relative names.
        windows = PureWindowsPath(raw)
        return bool(windows.drive) or raw.startswith(("\\\\", "//"))


def default_policy(root: str | os.PathLike[str] | None = None) -> SandboxPolicy:
    """Build a policy for *root* (defaults to the current directory)."""
    return SandboxPolicy(root=Path.cwd() if root is None else Path(root))


# Backwards-compatible module-level helpers used by the transitional tools.
_DEFAULT: SandboxPolicy | None = None


def _default() -> SandboxPolicy:
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = default_policy()
    return _DEFAULT


def safe_path(filename: str) -> Path:
    return _default().resolve(filename)


def get_base_dir() -> Path:
    return _default().root
