from __future__ import annotations

from pathlib import Path

import pytest

from dir_ai.diff import preview_edit, preview_write
from dir_ai.sandbox import PathEscapeError, SandboxPolicy


@pytest.fixture
def policy(tmp_path: Path) -> SandboxPolicy:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "existing.txt").write_text("old line\n", encoding="utf-8")
    (root / "latin1.txt").write_bytes(b"caf\xe9")
    return SandboxPolicy(root=root)


def test_new_file_diff(policy: SandboxPolicy) -> None:
    preview = preview_write(policy, "new.txt", "hello\n")
    assert preview.is_new is True
    assert preview.overwrite is False
    assert preview.noop is False
    assert "--- /dev/null" in preview.text
    assert "+++ b/new.txt" in preview.text
    assert "+hello" in preview.text


def test_overwrite_diff(policy: SandboxPolicy) -> None:
    preview = preview_write(policy, "existing.txt", "new line\n")
    assert preview.is_new is False
    assert preview.overwrite is True
    assert "-old line" in preview.text
    assert "+new line" in preview.text


def test_noop_write(policy: SandboxPolicy) -> None:
    preview = preview_write(policy, "existing.txt", "old line\n")
    assert preview.noop is True
    assert preview.text == ""


def test_large_diff_is_truncated(policy: SandboxPolicy) -> None:
    content = "".join(f"line {number}\n" for number in range(2000))
    preview = preview_write(policy, "big.txt", content, max_chars=200)
    assert preview.truncated is True
    assert "diff truncated" in preview.text
    assert len(preview.text) < 1000


def test_valid_edit_preview(policy: SandboxPolicy) -> None:
    preview = preview_edit(policy, "existing.txt", "old line", "new line")
    assert preview is not None
    assert "-old line" in preview.text
    assert "+new line" in preview.text


@pytest.mark.parametrize(
    ("filename", "old", "new"),
    [
        ("existing.txt", "", "x"),
        ("existing.txt", "same", "same"),
        ("existing.txt", "missing", "x"),
        ("missing.txt", "a", "b"),
        ("latin1.txt", "caf", "tea"),
        (".env", "a", "b"),
    ],
)
def test_invalid_edit_preview_returns_none(
    policy: SandboxPolicy, filename: str, old: str, new: str
) -> None:
    assert preview_edit(policy, filename, old, new) is None


def test_preview_write_rejects_escape(policy: SandboxPolicy) -> None:
    with pytest.raises(PathEscapeError):
        preview_write(policy, "../outside.txt", "x")
