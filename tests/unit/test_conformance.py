from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pytest

from dir_ai.approval import ApprovalKind, AutoApprove, AutoDeny
from dir_ai.execution import TOOL_KINDS, ToolExecutor
from dir_ai.policy import ApprovalPolicy, PolicyMode
from dir_ai.results import ErrorCode, ToolResult
from dir_ai.sandbox import SandboxPolicy
from dir_ai.tools.registry import build_tools

PACKAGE = Path(__file__).resolve().parents[2] / "dir_ai"
RAW_TOOL_IMPORTS = {
    "dir_ai.tools.write_file",
    "dir_ai.tools.edit_file",
    "dir_ai.tools.command",
}


def test_agent_layer_does_not_bypass_the_executor() -> None:
    offenders: list[str] = []
    for path in sorted((PACKAGE / "agent").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module in RAW_TOOL_IMPORTS:
                offenders.append(f"{path.name}:{node.lineno}: from {node.module} import ...")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in RAW_TOOL_IMPORTS:
                        offenders.append(f"{path.name}:{node.lineno}: import {alias.name}")
    assert offenders == [], "\n".join(offenders)


def test_registry_tools_are_executor_backed() -> None:
    source = (PACKAGE / "tools" / "registry.py").read_text(encoding="utf-8")
    assert "ToolExecutor" in source
    for method in TOOL_KINDS:
        if method == "run_command":
            continue  # wired to the registry in CP7
        assert f"active.{method}(" in source


def test_registry_names_match_executor_names(tmp_path: Path) -> None:
    policy = SandboxPolicy(root=tmp_path)
    tools = build_tools(policy, ToolExecutor(policy, AutoApprove()))
    assert {tool.name for tool in tools} == {
        "list_directory_tool",
        "read_file_tool",
        "write_file_tool",
        "edit_file_tool",
        "grep_tool",
        "glob_tool",
    }


def test_mutating_kinds_are_never_free_in_read_only() -> None:
    policy = ApprovalPolicy(PolicyMode.READ_ONLY)
    for kind in (ApprovalKind.WRITE, ApprovalKind.EDIT, ApprovalKind.COMMAND):
        decision = policy.decide(kind)
        assert decision.allowed is False
        assert decision.requires_approval is False


async def test_every_mutation_asks_for_approval(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("old\n", encoding="utf-8")
    policy = SandboxPolicy(root=tmp_path)

    async def runner(argv: list[str], **kwargs: Any) -> ToolResult:
        raise AssertionError("denied command must never run")

    cases = {
        "write_file": {"filename": "new.txt", "content": "hello\n"},
        "edit_file": {"filename": "app.py", "old": "old", "new": "new"},
        "run_command": {"argv": ["echo", "hi"]},
    }
    for name, arguments in cases.items():
        handler = AutoDeny()
        active = ToolExecutor(
            policy,
            handler,
            ApprovalPolicy(PolicyMode.AUTO_READ),
            command_runner=runner,
        )
        result = await active.call(name, **arguments)
        assert result.error_code == ErrorCode.DENIED, name
        assert len(handler.requests) == 1, name
        assert handler.requests[0].kind is TOOL_KINDS[name], name


@pytest.mark.parametrize(
    "name",
    ["list_directory", "read_file", "grep", "glob"],
)
async def test_reads_are_free_under_default_policy(tmp_path: Path, name: str) -> None:
    (tmp_path / "app.py").write_text("hello\n", encoding="utf-8")
    policy = SandboxPolicy(root=tmp_path)
    handler = AutoDeny()
    active = ToolExecutor(policy, handler)
    arguments = {
        "list_directory": {},
        "read_file": {"filename": "app.py"},
        "grep": {"pattern": "hello"},
        "glob": {"pattern": "*.py"},
    }[name]
    result = await active.call(name, **arguments)
    assert result.ok, result.output
    assert handler.requests == []
