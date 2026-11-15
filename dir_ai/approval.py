"""Approval protocol and handlers."""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from rich.console import Console

from dir_ai.diff import DiffPreview, preview_edit, preview_write
from dir_ai.sandbox import SandboxPolicy


class ApprovalKind(StrEnum):
    READ = "read"
    WRITE = "write"
    EDIT = "edit"
    COMMAND = "command"


@dataclass(frozen=True, slots=True)
class ApprovalRequest:
    request_id: str
    kind: ApprovalKind
    target: str
    diff: str = ""
    is_new: bool = False
    overwrite: bool = False
    noop: bool = False
    truncated: bool = False
    argv: tuple[str, ...] = ()
    cwd: str = ""
    timeout: float | None = None
    reason: str = ""

    @property
    def summary(self) -> str:
        if self.kind is ApprovalKind.COMMAND:
            return f"Run command: {' '.join(self.argv)}"
        if self.is_new:
            return f"{self.kind.value.title()} new file: {self.target}"
        return f"{self.kind.value.title()} existing file: {self.target}"


@dataclass(frozen=True, slots=True)
class ApprovalDecision:
    approved: bool
    note: str = ""
    timed_out: bool = False


class ApprovalHandler(Protocol):
    async def request(self, request: ApprovalRequest) -> ApprovalDecision: ...


class AutoApprove:
    def __init__(self, note: str = "auto-approved") -> None:
        self.note = note
        self.requests: list[ApprovalRequest] = []

    async def request(self, request: ApprovalRequest) -> ApprovalDecision:
        self.requests.append(request)
        return ApprovalDecision(True, note=self.note)


class AutoDeny:
    def __init__(self, note: str = "auto-denied") -> None:
        self.note = note
        self.requests: list[ApprovalRequest] = []

    async def request(self, request: ApprovalRequest) -> ApprovalDecision:
        self.requests.append(request)
        return ApprovalDecision(False, note=self.note)


def format_approval(request: ApprovalRequest) -> str:
    """Deterministic, plain-text rendering used by the CLI and snapshots."""
    lines = [f"Approval required: {request.summary}"]
    if request.is_new:
        lines.append("Label: new file")
    elif request.overwrite:
        lines.append("Label: overwrite existing file")
    if request.noop:
        lines.append("Label: no content change")
    if request.kind is ApprovalKind.COMMAND:
        lines.append(f"cwd: {request.cwd}")
        lines.append(f"timeout: {request.timeout if request.timeout is not None else 'none'}s")
        lines.append(f"argv: {list(request.argv)}")
    if request.reason:
        lines.append(f"reason: {request.reason}")
    if request.diff:
        lines.append("")
        lines.append(request.diff.rstrip("\n"))
    if request.truncated:
        lines.append("... [diff truncated for display]")
    return "\n".join(lines)


class CliApprovalHandler:
    """Prompts on an interactive terminal without blocking the event loop."""

    def __init__(
        self,
        console: Console | None = None,
        input_fn: Callable[[str], str] | None = None,
    ) -> None:
        self.console = console or Console()
        self.input_fn = input_fn or input

    async def request(self, request: ApprovalRequest) -> ApprovalDecision:
        return await asyncio.to_thread(self._ask, request)

    def _ask(self, request: ApprovalRequest) -> ApprovalDecision:
        self.console.print(format_approval(request))
        answer = self.input_fn("  Approve? [y/N] (deny with a note as 'n: reason'): ").strip()
        if answer.lower() in {"y", "yes"}:
            return ApprovalDecision(True, note="approved by user")
        note = ""
        if answer[:2].lower() == "n:":
            note = answer[2:].strip()
        return ApprovalDecision(False, note=note or "denied by user")


class RemoteApprovalHandler:
    """Placeholder for the CP9 WebSocket handler.

    ``request`` registers a future and waits; ``resolve`` completes it. A
    timeout, duplicate response, or unknown id is handled safely: timeout
    denies, duplicate/unknown responses are ignored.
    """

    def __init__(self, timeout: float = 60.0) -> None:
        self.timeout = timeout
        self._pending: dict[str, asyncio.Future[ApprovalDecision]] = {}

    @property
    def pending_ids(self) -> tuple[str, ...]:
        return tuple(self._pending)

    async def request(self, request: ApprovalRequest) -> ApprovalDecision:
        loop = asyncio.get_running_loop()
        future: asyncio.Future[ApprovalDecision] = loop.create_future()
        self._pending[request.request_id] = future
        try:
            return await asyncio.wait_for(future, self.timeout)
        except TimeoutError:
            return ApprovalDecision(False, note="approval timed out", timed_out=True)
        finally:
            self._pending.pop(request.request_id, None)

    def resolve(self, request_id: str, decision: ApprovalDecision) -> bool:
        future = self._pending.get(request_id)
        if future is None or future.done():
            return False
        future.set_result(decision)
        return True


def new_request_id() -> str:
    return f"req-{uuid.uuid4().hex[:12]}"


def request_for_write(
    policy: SandboxPolicy,
    filename: str,
    content: str,
    *,
    request_id: str | None = None,
) -> ApprovalRequest:
    preview = preview_write(policy, filename, content)
    return _from_preview(policy, ApprovalKind.WRITE, filename, preview, request_id)


def request_for_edit(
    policy: SandboxPolicy,
    filename: str,
    old: str,
    new: str,
    *,
    request_id: str | None = None,
) -> ApprovalRequest | None:
    preview = preview_edit(policy, filename, old, new)
    if preview is None:
        return None
    return _from_preview(policy, ApprovalKind.EDIT, filename, preview, request_id)


def request_for_command(
    argv: list[str],
    *,
    cwd: str,
    timeout: float | None,
    request_id: str | None = None,
    reason: str = "",
) -> ApprovalRequest:
    return ApprovalRequest(
        request_id=request_id or new_request_id(),
        kind=ApprovalKind.COMMAND,
        target=argv[0] if argv else "",
        argv=tuple(argv),
        cwd=cwd,
        timeout=timeout,
        reason=reason,
    )


def _from_preview(
    policy: SandboxPolicy,
    kind: ApprovalKind,
    filename: str,
    preview: DiffPreview,
    request_id: str | None,
) -> ApprovalRequest:
    path = policy.resolve(filename, operation="read" if kind is ApprovalKind.READ else "write")
    return ApprovalRequest(
        request_id=request_id or new_request_id(),
        kind=kind,
        target=policy.relative(path).as_posix(),
        diff=preview.text,
        is_new=preview.is_new,
        overwrite=preview.overwrite,
        noop=preview.noop,
        truncated=preview.truncated,
    )
