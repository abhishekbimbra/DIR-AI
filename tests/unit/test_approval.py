from __future__ import annotations

import asyncio
from io import StringIO
from pathlib import Path

import pytest
from rich.console import Console

from dir_ai.approval import (
    ApprovalDecision,
    ApprovalKind,
    ApprovalRequest,
    AutoApprove,
    AutoDeny,
    CliApprovalHandler,
    RemoteApprovalHandler,
    format_approval,
    new_request_id,
    request_for_command,
    request_for_edit,
    request_for_write,
)
from dir_ai.sandbox import SandboxPolicy


@pytest.fixture
def policy(tmp_path: Path) -> SandboxPolicy:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "app.py").write_text("print('old')\n", encoding="utf-8")
    return SandboxPolicy(root=root)


def write_request(policy: SandboxPolicy) -> ApprovalRequest:
    return request_for_write(policy, "new.txt", "hello\n", request_id="req-1")


def test_auto_handlers_record_requests() -> None:
    request = ApprovalRequest(request_id="r", kind=ApprovalKind.WRITE, target="x")
    approver = AutoApprove()
    denier = AutoDeny()

    assert asyncio.run(approver.request(request)).approved is True
    assert asyncio.run(denier.request(request)).approved is False
    assert approver.requests == [request]
    assert denier.requests == [request]


def test_request_ids_are_unique() -> None:
    first = new_request_id()
    second = new_request_id()
    assert first != second
    assert first.startswith("req-")


def test_write_request_labels(policy: SandboxPolicy) -> None:
    new = request_for_write(policy, "new.txt", "hello\n", request_id="req-new")
    assert new.kind is ApprovalKind.WRITE
    assert new.is_new is True
    assert new.overwrite is False
    assert "+hello" in new.diff

    overwrite = request_for_write(policy, "app.py", "print('new')\n", request_id="req-old")
    assert overwrite.is_new is False
    assert overwrite.overwrite is True
    assert "-print('old')" in overwrite.diff

    noop = request_for_write(policy, "app.py", "print('old')\n", request_id="req-noop")
    assert noop.noop is True
    assert noop.diff == ""


def test_edit_request_valid_and_invalid(policy: SandboxPolicy) -> None:
    request = request_for_edit(policy, "app.py", "old", "new", request_id="req-edit")
    assert request is not None
    assert request.kind is ApprovalKind.EDIT
    assert "-print('old')" in request.diff
    assert request_for_edit(policy, "app.py", "missing", "new") is None


def test_command_request_fields() -> None:
    request = request_for_command(
        ["pytest", "-q"], cwd="/work", timeout=5.0, request_id="req-cmd", reason="tests"
    )
    assert request.kind is ApprovalKind.COMMAND
    assert request.argv == ("pytest", "-q")
    assert request.target == "pytest"
    assert request.cwd == "/work"
    assert request.timeout == 5.0
    assert request.reason == "tests"
    assert request.summary == "Run command: pytest -q"


def test_format_write_and_command_rendering(policy: SandboxPolicy) -> None:
    write = write_request(policy)
    rendered = format_approval(write)
    assert "Approval required: Write new file: new.txt" in rendered
    assert "Label: new file" in rendered
    assert "--- /dev/null" in rendered

    command = request_for_command(["ls", "-la"], cwd="/work", timeout=None, request_id="req-c")
    command_text = format_approval(command)
    assert "cwd: /work" in command_text
    assert "timeout: nones" in command_text
    assert "argv: ['ls', '-la']" in command_text


def test_format_marks_truncation_and_noop(policy: SandboxPolicy) -> None:
    noop = request_for_write(policy, "app.py", "print('old')\n", request_id="req-n")
    assert "Label: no content change" in format_approval(noop)
    truncated = ApprovalRequest(
        request_id="req-t",
        kind=ApprovalKind.WRITE,
        target="x",
        diff="+x",
        truncated=True,
    )
    assert "[diff truncated for display]" in format_approval(truncated)


async def test_cli_approve_paths(policy: SandboxPolicy) -> None:
    output = StringIO()
    console = Console(file=output)
    request = write_request(policy)

    approved = await CliApprovalHandler(console=console, input_fn=lambda _: "y").request(request)
    assert approved.approved is True
    assert "Approval required" in output.getvalue()

    denied = await CliApprovalHandler(
        console=Console(file=StringIO()), input_fn=lambda _: "n: too risky"
    ).request(request)
    assert denied.approved is False
    assert denied.note == "too risky"

    bare_deny = await CliApprovalHandler(
        console=Console(file=StringIO()), input_fn=lambda _: "no"
    ).request(request)
    assert bare_deny.note == "denied by user"


async def test_remote_approval_round_trip() -> None:
    handler = RemoteApprovalHandler(timeout=1.0)
    request = ApprovalRequest(request_id="req-r", kind=ApprovalKind.WRITE, target="x")
    task = asyncio.create_task(handler.request(request))
    await asyncio.sleep(0)
    assert handler.pending_ids == ("req-r",)
    assert handler.resolve("wrong-id", ApprovalDecision(True)) is False
    assert handler.resolve("req-r", ApprovalDecision(True, note="ok")) is True
    decision = await task
    assert decision.approved is True
    assert decision.note == "ok"
    assert handler.resolve("req-r", ApprovalDecision(True)) is False


async def test_remote_approval_timeout_denies() -> None:
    handler = RemoteApprovalHandler(timeout=0.01)
    request = ApprovalRequest(request_id="req-timeout", kind=ApprovalKind.WRITE, target="x")
    decision = await handler.request(request)
    assert decision.approved is False
    assert decision.timed_out is True
    assert handler.pending_ids == ()
