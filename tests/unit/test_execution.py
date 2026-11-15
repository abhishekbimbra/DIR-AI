from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pytest

from dir_ai.approval import (
    ApprovalDecision,
    ApprovalHandler,
    ApprovalKind,
    ApprovalRequest,
    AutoApprove,
    AutoDeny,
)
from dir_ai.execution import TOOL_KINDS, ToolExecutor
from dir_ai.policy import ApprovalPolicy, PolicyMode
from dir_ai.results import ErrorCode, ToolResult
from dir_ai.sandbox import SandboxPolicy


@pytest.fixture
def sandbox(tmp_path: Path) -> SandboxPolicy:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "app.py").write_text("print('old')\n", encoding="utf-8")
    (root / "notes.txt").write_text("hello\n", encoding="utf-8")
    return SandboxPolicy(root=root)


def tree_hash(policy: SandboxPolicy) -> str:
    digest = hashlib.sha256()
    for entry in policy.walk(policy.root):
        if policy.is_file(entry):
            digest.update(policy.relative(entry).as_posix().encode())
            digest.update(policy.read_bytes(entry))
    return digest.hexdigest()


class TimedOutHandler:
    async def request(self, request: ApprovalRequest) -> ApprovalDecision:
        return ApprovalDecision(False, note="no answer", timed_out=True)


class RecordingHandler:
    def __init__(self) -> None:
        self.requests: list[ApprovalRequest] = []

    async def request(self, request: ApprovalRequest) -> ApprovalDecision:
        self.requests.append(request)
        return ApprovalDecision(True)


def executor(
    sandbox: SandboxPolicy,
    approval: ApprovalHandler,
    mode: PolicyMode = PolicyMode.AUTO_READ,
    **kwargs: Any,
) -> ToolExecutor:
    return ToolExecutor(sandbox, approval, ApprovalPolicy(mode=mode), **kwargs)


async def test_approved_write_changes_file(sandbox: SandboxPolicy) -> None:
    result = await executor(sandbox, AutoApprove()).write_file("new.txt", "hello\n")
    assert result.ok
    assert (sandbox.root / "new.txt").read_text(encoding="utf-8") == "hello\n"


async def test_denied_write_leaves_filesystem_untouched(sandbox: SandboxPolicy) -> None:
    before = tree_hash(sandbox)
    handler = AutoDeny(note="not today")
    result = await executor(sandbox, handler).write_file("new.txt", "hello\n")
    assert result.ok is False
    assert result.error_code == ErrorCode.DENIED
    assert "not today" in result.output
    assert tree_hash(sandbox) == before


async def test_denied_edit_leaves_file_untouched(sandbox: SandboxPolicy) -> None:
    before = tree_hash(sandbox)
    result = await executor(sandbox, AutoDeny()).edit_file("app.py", "old", "new")
    assert result.error_code == ErrorCode.DENIED
    assert tree_hash(sandbox) == before


async def test_approved_edit_changes_file(sandbox: SandboxPolicy) -> None:
    result = await executor(sandbox, AutoApprove()).edit_file("app.py", "old", "new")
    assert result.ok
    assert "new" in (sandbox.root / "app.py").read_text(encoding="utf-8")


async def test_read_only_denies_without_prompt(sandbox: SandboxPolicy) -> None:
    handler = AutoApprove()
    result = await executor(sandbox, handler, PolicyMode.READ_ONLY).write_file("x.txt", "x")
    assert result.error_code == ErrorCode.DENIED
    assert handler.requests == []
    assert not (sandbox.root / "x.txt").exists()


async def test_auto_read_does_not_prompt_for_reads(sandbox: SandboxPolicy) -> None:
    handler = AutoApprove()
    result = await executor(sandbox, handler).read_file("app.py")
    assert result.ok
    assert handler.requests == []


async def test_ask_all_prompts_for_reads(sandbox: SandboxPolicy) -> None:
    handler = AutoApprove()
    result = await executor(sandbox, handler, PolicyMode.ASK_ALL).read_file("app.py")
    assert result.ok
    assert len(handler.requests) == 1
    assert handler.requests[0].kind is ApprovalKind.READ


async def test_invalid_edit_errors_without_prompt(sandbox: SandboxPolicy) -> None:
    handler = AutoApprove()
    result = await executor(sandbox, handler).edit_file("app.py", "missing", "new")
    assert result.error_code == ErrorCode.NO_MATCH
    assert handler.requests == []


async def test_timeout_denies(sandbox: SandboxPolicy) -> None:
    result = await executor(sandbox, TimedOutHandler()).write_file("x.txt", "x")
    assert result.ok is False
    assert "timed out" in result.output


async def test_write_request_carries_diff(sandbox: SandboxPolicy) -> None:
    handler = RecordingHandler()
    await executor(sandbox, handler).write_file("new.txt", "hello\n")
    assert len(handler.requests) == 1
    assert handler.requests[0].kind is ApprovalKind.WRITE
    assert "+hello" in handler.requests[0].diff
    assert handler.requests[0].is_new


async def test_command_approved_runs(sandbox: SandboxPolicy) -> None:
    calls: list[dict[str, Any]] = []

    async def runner(argv: list[str], **kwargs: Any) -> ToolResult:
        calls.append({"argv": argv, **kwargs})
        return ToolResult.success("ok")

    handler = AutoApprove()
    result = await executor(sandbox, handler, command_runner=runner).run_command(
        ["echo", "hi"], cwd=".", timeout=3
    )
    assert result.ok
    assert handler.requests[0].kind is ApprovalKind.COMMAND
    assert handler.requests[0].argv == ("echo", "hi")
    assert calls[0]["argv"] == ["echo", "hi"]
    assert calls[0]["timeout"] == 3
    assert Path(calls[0]["cwd"]) == sandbox.root
    assert calls[0]["sandbox"] is sandbox


async def test_denied_command_never_runs(sandbox: SandboxPolicy) -> None:
    calls: list[list[str]] = []

    async def runner(argv: list[str], **kwargs: Any) -> ToolResult:
        calls.append(argv)
        return ToolResult.success("should not happen")

    result = await executor(sandbox, AutoDeny(), command_runner=runner).run_command(["ls"])
    assert result.error_code == ErrorCode.DENIED
    assert calls == []


async def test_command_without_runner_fails_after_approval(sandbox: SandboxPolicy) -> None:
    result = await executor(sandbox, AutoApprove()).run_command(["ls"])
    assert result.error_code == ErrorCode.INVALID_ARGUMENT


async def test_command_validation(sandbox: SandboxPolicy) -> None:
    handler = AutoApprove()
    assert (
        await executor(sandbox, handler).run_command([])
    ).error_code == ErrorCode.INVALID_ARGUMENT
    escaped = await executor(sandbox, handler).run_command(["ls"], cwd="../")
    assert escaped.error_code == ErrorCode.DENIED


async def test_call_dispatch_and_errors(sandbox: SandboxPolicy) -> None:
    active = executor(sandbox, AutoApprove())
    assert (await active.call("read_file", filename="app.py")).ok
    assert (await active.call("missing_tool")).error_code == ErrorCode.INVALID_ARGUMENT
    assert (await active.call("read_file", nonsense=True)).error_code == ErrorCode.INVALID_ARGUMENT


def test_tool_kind_map_is_complete() -> None:
    assert set(TOOL_KINDS) == {
        "list_directory",
        "read_file",
        "grep",
        "glob",
        "write_file",
        "edit_file",
        "run_command",
    }
    assert TOOL_KINDS["write_file"] is ApprovalKind.WRITE
    assert TOOL_KINDS["edit_file"] is ApprovalKind.EDIT
    assert TOOL_KINDS["run_command"] is ApprovalKind.COMMAND
