"""Tool execution layer: every tool call passes through policy and approval."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from dir_ai.approval import (
    ApprovalDecision,
    ApprovalHandler,
    ApprovalKind,
    ApprovalRequest,
    new_request_id,
    request_for_command,
    request_for_edit,
    request_for_write,
)
from dir_ai.policy import ApprovalPolicy, PolicyMode
from dir_ai.results import ErrorCode, ToolResult
from dir_ai.sandbox import SandboxError, SandboxPolicy
from dir_ai.tools.edit_file import edit_file
from dir_ai.tools.glob import glob_paths
from dir_ai.tools.grep import grep
from dir_ai.tools.list_directory import list_directory
from dir_ai.tools.read_file import read_file
from dir_ai.tools.write_file import write_file

CommandRunner = Callable[..., Awaitable[ToolResult]]

TOOL_KINDS: dict[str, ApprovalKind] = {
    "list_directory": ApprovalKind.READ,
    "read_file": ApprovalKind.READ,
    "grep": ApprovalKind.READ,
    "glob": ApprovalKind.READ,
    "write_file": ApprovalKind.WRITE,
    "edit_file": ApprovalKind.EDIT,
    "run_command": ApprovalKind.COMMAND,
}


class ToolExecutor:
    """The only supported path from an agent/tool call to the filesystem.

    Reads honour the policy (and prompt under ``ask-all``); writes, edits, and
    commands always pass through the configured approval handler unless the
    policy denies them outright.
    """

    def __init__(
        self,
        sandbox: SandboxPolicy,
        approval: ApprovalHandler,
        approval_policy: ApprovalPolicy | None = None,
        *,
        request_id_factory: Callable[[], str] = new_request_id,
        command_runner: CommandRunner | None = None,
    ) -> None:
        self.sandbox = sandbox
        self.approval = approval
        self.approval_policy = approval_policy or ApprovalPolicy()
        self.request_id_factory = request_id_factory
        self.command_runner = command_runner

    async def _authorize(
        self, kind: ApprovalKind, request: ApprovalRequest | None
    ) -> ToolResult | None:
        decision = self.approval_policy.decide(kind)
        if not decision.allowed:
            return ToolResult.failure(
                ErrorCode.DENIED,
                f"Policy '{self.approval_policy.mode.value}' does not allow {kind.value}.",
            )
        if not decision.requires_approval:
            return None
        if request is None:
            return ToolResult.failure(
                ErrorCode.INVALID_ARGUMENT, f"{kind.value} request could not be prepared."
            )
        outcome = await self.approval.request(request)
        if outcome.approved:
            return None
        if outcome.timed_out:
            note = f"approval timed out ({outcome.note})" if outcome.note else "approval timed out"
        else:
            note = outcome.note or "denied"
        return ToolResult.failure(ErrorCode.DENIED, f"{kind.value} denied: {note}")

    def _read_request(self, target: str) -> ApprovalRequest:
        return ApprovalRequest(
            request_id=self.request_id_factory(),
            kind=ApprovalKind.READ,
            target=target,
        )

    async def list_directory(
        self, path: str = ".", recursive: bool = False, max_entries: int = 500
    ) -> ToolResult:
        denied = await self._authorize(ApprovalKind.READ, self._read_request(path))
        if denied:
            return denied
        return list_directory(self.sandbox, path=path, recursive=recursive, max_entries=max_entries)

    async def read_file(self, filename: str, offset: int = 0, limit: int = 200) -> ToolResult:
        denied = await self._authorize(ApprovalKind.READ, self._read_request(filename))
        if denied:
            return denied
        return read_file(self.sandbox, filename, offset=offset, limit=limit)

    async def grep(
        self,
        pattern: str,
        path: str = ".",
        max_results: int = 100,
        case_sensitive: bool = True,
    ) -> ToolResult:
        denied = await self._authorize(ApprovalKind.READ, self._read_request(path))
        if denied:
            return denied
        return grep(
            self.sandbox,
            pattern,
            path=path,
            max_results=max_results,
            case_sensitive=case_sensitive,
        )

    async def glob(self, pattern: str, path: str = ".", max_results: int = 200) -> ToolResult:
        denied = await self._authorize(ApprovalKind.READ, self._read_request(path))
        if denied:
            return denied
        return glob_paths(self.sandbox, pattern, path=path, max_results=max_results)

    async def write_file(self, filename: str, content: str) -> ToolResult:
        try:
            request = request_for_write(
                self.sandbox, filename, content, request_id=self.request_id_factory()
            )
        except SandboxError as exc:
            return ToolResult.failure(ErrorCode.DENIED, str(exc))
        denied = await self._authorize(ApprovalKind.WRITE, request)
        if denied:
            return denied
        return write_file(self.sandbox, filename, content)

    async def edit_file(self, filename: str, old: str, new: str) -> ToolResult:
        decision = self.approval_policy.decide(ApprovalKind.EDIT)
        if not decision.allowed:
            return ToolResult.failure(
                ErrorCode.DENIED,
                f"Policy '{self.approval_policy.mode.value}' does not allow edit.",
            )
        request = request_for_edit(
            self.sandbox, filename, old, new, request_id=self.request_id_factory()
        )
        if request is None:
            # Invalid edit: let the tool produce the precise error without a prompt.
            return edit_file(self.sandbox, filename, old, new)
        denied = await self._authorize(ApprovalKind.EDIT, request)
        if denied:
            return denied
        return edit_file(self.sandbox, filename, old, new)

    async def run_command(
        self,
        argv: list[str],
        cwd: str = ".",
        timeout: float = 30.0,
        reason: str = "",
    ) -> ToolResult:
        try:
            resolved_cwd = self.sandbox.resolve(cwd, operation="list")
        except SandboxError as exc:
            return ToolResult.failure(ErrorCode.DENIED, str(exc))
        if not argv:
            return ToolResult.failure(ErrorCode.INVALID_ARGUMENT, "argv must not be empty.")
        request = request_for_command(
            argv,
            cwd=str(resolved_cwd),
            timeout=timeout,
            request_id=self.request_id_factory(),
            reason=reason,
        )
        denied = await self._authorize(ApprovalKind.COMMAND, request)
        if denied:
            return denied
        if self.command_runner is None:
            return ToolResult.failure(
                ErrorCode.INVALID_ARGUMENT, "Command execution is not configured."
            )
        return await self.command_runner(
            argv, cwd=resolved_cwd, timeout=timeout, sandbox=self.sandbox
        )

    async def call(self, name: str, /, **arguments: object) -> ToolResult:
        """Dispatch by tool name; unknown names and bad arguments never crash."""
        kind = TOOL_KINDS.get(name)
        if kind is None:
            return ToolResult.failure(ErrorCode.INVALID_ARGUMENT, f"Unknown tool: {name}")
        try:
            result = await getattr(self, name)(**arguments)
        except TypeError as exc:
            return ToolResult.failure(ErrorCode.INVALID_ARGUMENT, f"Bad arguments: {exc}")
        return result


def decision_allows_execution(
    executor: ToolExecutor, kind: ApprovalKind, decision: ApprovalDecision
) -> bool:
    """Small helper for tests and callers that need the policy verdict."""
    return executor.approval_policy.decide(kind).allowed and decision.approved


__all__ = [
    "TOOL_KINDS",
    "ApprovalPolicy",
    "PolicyMode",
    "ToolExecutor",
    "decision_allows_execution",
]
