from __future__ import annotations

import os
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import settings as hypothesis_settings
from hypothesis import strategies as st

from dir_ai.sandbox import (
    DeniedPathError,
    FileTooLargeError,
    OperationDeniedError,
    PathEscapeError,
    SandboxError,
    SandboxPolicy,
    default_policy,
    get_base_dir,
    safe_path,
)


@pytest.fixture
def policy(tmp_path: Path) -> SandboxPolicy:
    root = tmp_path / "proj"
    root.mkdir()
    (root / "pkg").mkdir()
    (root / "pkg" / "app.py").write_text("print('hi')\n", encoding="utf-8")
    (tmp_path / "proj-secrets").mkdir()
    (tmp_path / "proj-secrets" / "token.txt").write_text("secret", encoding="utf-8")
    return SandboxPolicy(root=root)


def test_resolves_nested_file(policy: SandboxPolicy) -> None:
    assert policy.resolve("pkg/app.py") == policy.root / "pkg" / "app.py"


def test_resolves_root_itself(policy: SandboxPolicy) -> None:
    assert policy.resolve(".") == policy.root


@pytest.mark.parametrize(
    "candidate",
    [
        "../proj-secrets/token.txt",
        "../../etc/passwd",
        "pkg/../../proj-secrets/token.txt",
        "..",
        "/etc/passwd",
        "/tmp/whatever",
        "",
        "   ",
        "bad\x00name",
        "C:\\Windows\\System32\\config",
        "C:relative-drive",
        "\\\\server\\share\\file",
        "//server/share/file",
        "a" * 5000,
        "a" * 300,
    ],
)
def test_rejects_escapes_and_malformed_paths(policy: SandboxPolicy, candidate: str) -> None:
    with pytest.raises(SandboxError):
        policy.resolve(candidate)


def test_rejects_bytes_path(policy: SandboxPolicy) -> None:
    with pytest.raises(SandboxError, match="text"):
        policy.resolve(b"pkg/app.py")  # type: ignore[arg-type]


def test_sibling_prefix_cannot_escape(policy: SandboxPolicy) -> None:
    with pytest.raises(PathEscapeError):
        policy.resolve("../proj-secrets/token.txt")


def test_symlink_to_outside_is_rejected(policy: SandboxPolicy, tmp_path: Path) -> None:
    outside = tmp_path / "outside.txt"
    outside.write_text("nope", encoding="utf-8")
    link = policy.root / "escape.txt"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable on this platform")
    with pytest.raises(PathEscapeError):
        policy.resolve("escape.txt")


def test_symlink_inside_is_allowed(policy: SandboxPolicy) -> None:
    link = policy.root / "alias.py"
    try:
        link.symlink_to(policy.root / "pkg" / "app.py")
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable on this platform")
    assert policy.resolve("alias.py") == policy.root / "pkg" / "app.py"


@pytest.mark.parametrize(
    "candidate",
    [
        ".env",
        ".ENV",
        "config/.env.local",
        ".env.production",
        ".git/config",
        "repo/.git/HEAD",
        "keys/server.pem",
        ".ssh/id_rsa",
        "id_rsa",
        "id_ed25519.pub",
        "vault.kdbx",
        ".aws/credentials",
    ],
)
def test_denylist_blocks_secrets_and_internals(policy: SandboxPolicy, candidate: str) -> None:
    with pytest.raises(DeniedPathError):
        policy.resolve(candidate)


@pytest.mark.parametrize(
    "candidate",
    [
        "README.md",
        "pkg/app.py",
        "src/.envrc-safe.txt",
        "docs/key-notes.md",
        ".github/workflows/ci.yml",
    ],
)
def test_normal_files_are_allowed(policy: SandboxPolicy, candidate: str) -> None:
    assert policy.resolve(candidate).is_relative_to(policy.root)


def test_unicode_lookalikes_stay_contained(policy: SandboxPolicy) -> None:
    for candidate in ("\u2024\u2024/x", "\uff0e\uff0e/x", "na\u00efve.txt"):
        try:
            resolved = policy.resolve(candidate)
        except SandboxError:
            continue
        assert resolved.is_relative_to(policy.root)


def test_operation_must_be_allowed(tmp_path: Path) -> None:
    policy = SandboxPolicy(root=tmp_path, allowed_operations=frozenset({"read"}))
    assert policy.resolve("file.txt", operation="read").is_relative_to(tmp_path)
    with pytest.raises(OperationDeniedError):
        policy.resolve("file.txt", operation="write")


def test_custom_policy_validation(tmp_path: Path) -> None:
    with pytest.raises(PathEscapeError):
        SandboxPolicy(root=tmp_path / "missing")
    file_path = tmp_path / "file.txt"
    file_path.write_text("x", encoding="utf-8")
    with pytest.raises(PathEscapeError):
        SandboxPolicy(root=file_path)
    with pytest.raises(SandboxError, match="positive"):
        SandboxPolicy(root=tmp_path, max_file_size=0)
    with pytest.raises(SandboxError, match="Unknown operations"):
        SandboxPolicy(root=tmp_path, allowed_operations=frozenset({"delete"}))


def test_relative_and_size_checks(policy: SandboxPolicy) -> None:
    target = policy.root / "pkg" / "app.py"
    assert policy.relative(target) == Path("pkg/app.py")
    with pytest.raises(PathEscapeError):
        policy.relative(policy.root.parent)

    policy.check_size(target)
    policy.check_size(policy.root / "missing.txt")  # no file: no error
    big = policy.root / "big.txt"
    big.write_text("x" * 32, encoding="utf-8")
    small_policy = SandboxPolicy(root=policy.root, max_file_size=8)
    with pytest.raises(FileTooLargeError):
        small_policy.check_size(big)


def test_ensure_parent_creates_directories(policy: SandboxPolicy) -> None:
    target = policy.root / "new" / "deep" / "file.txt"
    policy.ensure_parent(target)
    assert target.parent.is_dir()


def test_ensure_parent_rejects_outside(policy: SandboxPolicy) -> None:
    with pytest.raises(PathEscapeError):
        policy.ensure_parent(policy.root.parent / "evil" / "file.txt")


def test_default_policy_and_legacy_helpers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    policy = default_policy()
    assert policy.root == tmp_path.resolve()
    assert safe_path("x.txt") == tmp_path.resolve() / "x.txt"
    assert get_base_dir() == tmp_path.resolve()


def test_windows_path_detection() -> None:
    assert SandboxPolicy._looks_like_windows_absolute("C:\\x")
    assert SandboxPolicy._looks_like_windows_absolute("\\\\server\\share")
    assert not SandboxPolicy._looks_like_windows_absolute("pkg/app.py")


@hypothesis_settings(max_examples=3000, deadline=None)
@given(st.text())
def test_property_every_path_is_inside_or_rejected(candidate: str) -> None:
    """Any generated path either resolves inside the root or raises SandboxError."""
    root = Path.cwd()
    policy = SandboxPolicy(root=root)
    try:
        resolved = policy.resolve(candidate)
    except SandboxError:
        return
    assert resolved.is_relative_to(root)


def test_hypothesis_environment_sanity() -> None:
    assert os.name in {"posix", "nt"}
