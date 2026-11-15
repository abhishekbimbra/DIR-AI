from __future__ import annotations

import contextlib
from pathlib import Path

import pytest

from dir_ai.sandbox import FileTooLargeError, SandboxPolicy


@pytest.fixture
def policy(tmp_path: Path) -> SandboxPolicy:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "a.txt").write_text("hello", encoding="utf-8")
    (root / "sub").mkdir()
    (root / "sub" / "b.py").write_text("x = 1\n", encoding="utf-8")
    (root / ".env").write_text("SECRET=1\n", encoding="utf-8")
    outside = tmp_path / "outside.txt"
    outside.write_text("nope", encoding="utf-8")
    with contextlib.suppress(OSError, NotImplementedError):
        (root / "escape.txt").symlink_to(outside)
    return SandboxPolicy(root=root)


def test_stat_helpers(policy: SandboxPolicy) -> None:
    target = policy.root / "a.txt"
    assert policy.exists(target)
    assert policy.is_file(target)
    assert not policy.is_dir(target)
    assert policy.stat_size(target) == 5
    assert policy.is_dir(policy.root / "sub")


def test_read_bytes_and_limits(policy: SandboxPolicy) -> None:
    target = policy.root / "a.txt"
    assert policy.read_bytes(target) == b"hello"
    assert policy.read_bytes(target, max_bytes=5) == b"hello"
    with pytest.raises(FileTooLargeError):
        policy.read_bytes(target, max_bytes=4)
    with pytest.raises(FileTooLargeError):
        policy.read_bytes(target, max_bytes=2)


def test_read_text_replaces_invalid_utf8(policy: SandboxPolicy) -> None:
    path = policy.root / "latin1.txt"
    path.write_bytes(b"caf\xe9")
    assert "caf" in policy.read_text(path)


def test_write_text_creates_parents(policy: SandboxPolicy) -> None:
    target = policy.root / "deep" / "nested" / "file.txt"
    assert policy.write_text(target, "content") == 7
    assert target.read_text(encoding="utf-8") == "content"


def test_iter_dir_and_walk(policy: SandboxPolicy) -> None:
    names = [entry.name for entry in policy.iter_dir(policy.root)]
    assert names == sorted(names, key=str.lower)
    walked = {entry.name for entry in policy.walk(policy.root)}
    assert {"a.txt", "b.py", "sub"} <= walked


def test_glob_paths_hides_denied_and_escapes(policy: SandboxPolicy) -> None:
    matches = policy.glob_paths(policy.root, "**/*")
    rendered = {policy.relative(match).as_posix() for match in matches}
    assert "a.txt" in rendered
    assert "sub/b.py" in rendered
    assert ".env" not in rendered
    assert "escape.txt" not in rendered


def test_is_denied(policy: SandboxPolicy) -> None:
    assert policy.is_denied(policy.root / ".env")
    assert policy.is_denied(policy.root / "escape.txt")
    assert policy.is_denied(policy.root.parent / "outside.txt")
    assert not policy.is_denied(policy.root / "a.txt")
    assert policy.is_denied("../a.txt")
