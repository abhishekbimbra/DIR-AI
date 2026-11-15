from __future__ import annotations

from pathlib import Path

from syrupy.assertion import SnapshotAssertion

from dir_ai.approval import format_approval, request_for_command, request_for_write
from dir_ai.sandbox import SandboxPolicy


def test_write_approval_rendering_is_stable(snapshot: SnapshotAssertion, tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "app.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    policy = SandboxPolicy(root=root)

    request = request_for_write(
        policy,
        "app.py",
        "def add(a, b):\n    return a - b\n",
        request_id="req-snapshot-write",
    )
    assert format_approval(request) == snapshot


def test_command_approval_rendering_is_stable(snapshot: SnapshotAssertion) -> None:
    request = request_for_command(
        ["pytest", "-q", "tests/unit"],
        cwd="/work/repo",
        timeout=30.0,
        request_id="req-snapshot-command",
        reason="run unit tests",
    )
    assert format_approval(request) == snapshot
