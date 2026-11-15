from __future__ import annotations

import json
from pathlib import Path

import pytest

from dir_ai.approval import AutoApprove
from dir_ai.execution import ToolExecutor
from dir_ai.results import ErrorCode
from dir_ai.sandbox import SandboxPolicy
from dir_ai.tools.edit_file import edit_file
from dir_ai.tools.glob import glob_paths
from dir_ai.tools.grep import grep
from dir_ai.tools.list_directory import list_directory
from dir_ai.tools.read_file import read_file
from dir_ai.tools.registry import build_tools
from dir_ai.tools.write_file import write_file


@pytest.fixture
def policy(tmp_path: Path) -> SandboxPolicy:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "app.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    (root / "empty.txt").write_text("", encoding="utf-8")
    (root / "crlf.txt").write_bytes(b"one\r\ntwo\r\n")
    (root / "latin1.txt").write_bytes(b"caf\xe9\n")
    (root / "binary.bin").write_bytes(b"\x00\x01\x02")
    (root / "ambiguous.txt").write_text("foo foo\n", encoding="utf-8")
    (root / ".gitignore").write_text("ignored/\n*.log\n", encoding="utf-8")
    (root / "debug.log").write_text("secret log\n", encoding="utf-8")
    (root / "ignored").mkdir()
    (root / "ignored" / "hidden.txt").write_text("hidden\n", encoding="utf-8")
    (root / "sub").mkdir()
    (root / "sub" / "nested.py").write_text("print('nested')\n", encoding="utf-8")
    (root / ".env").write_text("TOKEN=supersecret\n", encoding="utf-8")
    (root / ".git").mkdir()
    (root / ".git" / "config").write_text("[core]\n", encoding="utf-8")
    return SandboxPolicy(root=root)


def ok(result: object) -> str:
    from dir_ai.results import ToolResult

    assert isinstance(result, ToolResult)
    assert result.ok is True, result.output
    return result.output


def fail(result: object, code: ErrorCode) -> str:
    from dir_ai.results import ToolResult

    assert isinstance(result, ToolResult)
    assert result.ok is False
    assert result.error_code == code, result.output
    return result.output


# -- list_directory -----------------------------------------------------------


def test_list_flat_hides_ignored_and_denied(policy: SandboxPolicy) -> None:
    output = ok(list_directory(policy))
    assert "app.py" in output
    assert "sub" in output
    assert "debug.log" not in output
    assert "ignored" not in output
    assert ".env" not in output
    assert "[DIR] .git" not in output
    assert ".gitignore" in output


def test_list_recursive_uses_relative_paths(policy: SandboxPolicy) -> None:
    output = ok(list_directory(policy, recursive=True))
    assert "sub/nested.py" in output
    assert "ignored/hidden.txt" not in output


def test_list_errors(policy: SandboxPolicy) -> None:
    fail(list_directory(policy, "missing"), ErrorCode.NOT_FOUND)
    fail(list_directory(policy, "app.py"), ErrorCode.NOT_A_DIRECTORY)
    fail(list_directory(policy, "../"), ErrorCode.DENIED)
    fail(list_directory(policy, max_entries=0), ErrorCode.INVALID_ARGUMENT)


def test_list_truncates(policy: SandboxPolicy) -> None:
    from dir_ai.results import ToolResult

    result = list_directory(policy, max_entries=1)
    assert isinstance(result, ToolResult)
    assert result.ok and result.truncated


# -- read_file ----------------------------------------------------------------


def test_read_whole_file(policy: SandboxPolicy) -> None:
    output = ok(read_file(policy, "app.py"))
    assert "return a + b" in output
    assert "lines 1-2 of 2" in output


def test_read_paging(policy: SandboxPolicy) -> None:
    output = ok(read_file(policy, "app.py", offset=1, limit=1))
    assert "return a + b" in output
    assert "def add" not in output


def test_read_preserves_crlf(policy: SandboxPolicy) -> None:
    assert "\r\n" in ok(read_file(policy, "crlf.txt"))


def test_read_empty_file(policy: SandboxPolicy) -> None:
    assert ok(read_file(policy, "empty.txt")) == ""


def test_read_errors(policy: SandboxPolicy) -> None:
    fail(read_file(policy, "missing.txt"), ErrorCode.NOT_FOUND)
    fail(read_file(policy, "sub"), ErrorCode.NOT_A_FILE)
    fail(read_file(policy, "binary.bin"), ErrorCode.BINARY)
    fail(read_file(policy, ".env"), ErrorCode.DENIED)
    fail(read_file(policy, "app.py", offset=-1), ErrorCode.INVALID_ARGUMENT)
    fail(read_file(policy, "app.py", limit=0), ErrorCode.INVALID_ARGUMENT)
    fail(read_file(policy, "app.py", limit=99_999), ErrorCode.INVALID_ARGUMENT)


def test_read_non_utf8_is_replaced_not_crashed(policy: SandboxPolicy) -> None:
    output = ok(read_file(policy, "latin1.txt"))
    assert "caf" in output


def test_read_too_large(policy: SandboxPolicy) -> None:
    small = SandboxPolicy(root=policy.root, max_file_size=4)
    fail(read_file(small, "app.py"), ErrorCode.TOO_LARGE)


# -- write_file ---------------------------------------------------------------


def test_write_creates_parents(policy: SandboxPolicy) -> None:
    ok(write_file(policy, "new/deep/file.txt", "hello"))
    assert (policy.root / "new" / "deep" / "file.txt").read_text(encoding="utf-8") == "hello"


def test_write_overwrites(policy: SandboxPolicy) -> None:
    ok(write_file(policy, "app.py", "replaced"))
    assert (policy.root / "app.py").read_text(encoding="utf-8") == "replaced"


def test_write_errors(policy: SandboxPolicy) -> None:
    fail(write_file(policy, "sub", "x"), ErrorCode.IS_A_DIRECTORY)
    fail(write_file(policy, ".env", "x"), ErrorCode.DENIED)
    fail(write_file(policy, ".git/config", "x"), ErrorCode.DENIED)
    fail(write_file(policy, "../outside.txt", "x"), ErrorCode.DENIED)


# -- edit_file ----------------------------------------------------------------


def test_edit_single_match(policy: SandboxPolicy) -> None:
    ok(edit_file(policy, "app.py", "return a + b", "return a - b"))
    assert "return a - b" in (policy.root / "app.py").read_text(encoding="utf-8")


def test_edit_zero_and_multiple_matches(policy: SandboxPolicy) -> None:
    fail(edit_file(policy, "app.py", "not-there", "x"), ErrorCode.NO_MATCH)
    fail(edit_file(policy, "ambiguous.txt", "foo", "bar"), ErrorCode.AMBIGUOUS)


def test_edit_is_whitespace_sensitive(policy: SandboxPolicy) -> None:
    fail(edit_file(policy, "app.py", "\treturn a + b", "return a + b"), ErrorCode.NO_MATCH)
    ok(edit_file(policy, "app.py", "    return a + b", "        return a + b"))


def test_edit_is_idempotent(policy: SandboxPolicy) -> None:
    ok(edit_file(policy, "app.py", "return a + b", "return a * b"))
    before = (policy.root / "app.py").read_bytes()
    fail(edit_file(policy, "app.py", "return a + b", "return a * b"), ErrorCode.NO_MATCH)
    assert (policy.root / "app.py").read_bytes() == before


def test_edit_argument_errors(policy: SandboxPolicy) -> None:
    fail(edit_file(policy, "app.py", "", "x"), ErrorCode.INVALID_ARGUMENT)
    fail(edit_file(policy, "app.py", "same", "same"), ErrorCode.INVALID_ARGUMENT)
    fail(edit_file(policy, "missing.py", "a", "b"), ErrorCode.NOT_FOUND)
    fail(edit_file(policy, "binary.bin", "a", "b"), ErrorCode.BINARY)


# -- grep ---------------------------------------------------------------------


def test_grep_finds_matches_with_paths(policy: SandboxPolicy) -> None:
    output = ok(grep(policy, r"return a \+ b"))
    assert "app.py:2:" in output


def test_grep_ignores_gitignored_and_denied(policy: SandboxPolicy) -> None:
    assert ok(grep(policy, "secret")) == "No matches."
    assert ok(grep(policy, "TOKEN")) == "No matches."


def test_grep_case_sensitivity(policy: SandboxPolicy) -> None:
    assert ok(grep(policy, "DEF", case_sensitive=False)) != "No matches."
    assert ok(grep(policy, "DEF", case_sensitive=True)) == "No matches."


def test_grep_limits_and_errors(policy: SandboxPolicy) -> None:
    from dir_ai.results import ToolResult

    result = grep(policy, r"\w+", max_results=1)
    assert isinstance(result, ToolResult)
    assert result.truncated
    fail(grep(policy, "["), ErrorCode.INVALID_ARGUMENT)
    fail(grep(policy, ""), ErrorCode.INVALID_ARGUMENT)
    fail(grep(policy, "x", max_results=0), ErrorCode.INVALID_ARGUMENT)
    fail(grep(policy, "x", path="missing"), ErrorCode.NOT_FOUND)
    fail(grep(policy, "x", path="../"), ErrorCode.DENIED)
    assert ok(grep(policy, "print", path="sub")) != "No matches."


def test_grep_on_single_file(policy: SandboxPolicy) -> None:
    assert "app.py:1:" in ok(grep(policy, "def add", path="app.py"))


def test_grep_skips_binary(policy: SandboxPolicy) -> None:
    assert ok(grep(policy, "\x00", path="binary.bin")) == "No matches."


# -- glob ---------------------------------------------------------------------


def test_glob_recursive(policy: SandboxPolicy) -> None:
    output = ok(glob_paths(policy, "**/*.py"))
    assert "app.py" in output
    assert "sub/nested.py" in output


def test_glob_excludes_ignored(policy: SandboxPolicy) -> None:
    assert ok(glob_paths(policy, "*.log")) == "No matches."


def test_glob_errors(policy: SandboxPolicy) -> None:
    fail(glob_paths(policy, ""), ErrorCode.INVALID_ARGUMENT)
    fail(glob_paths(policy, "../*"), ErrorCode.INVALID_ARGUMENT)
    fail(glob_paths(policy, "/etc/*"), ErrorCode.INVALID_ARGUMENT)
    fail(glob_paths(policy, "C:\\*"), ErrorCode.INVALID_ARGUMENT)
    fail(glob_paths(policy, "*.py", path="missing"), ErrorCode.NOT_FOUND)
    fail(glob_paths(policy, "*.py", path="app.py"), ErrorCode.NOT_A_DIRECTORY)
    fail(glob_paths(policy, "*.py", max_results=0), ErrorCode.INVALID_ARGUMENT)


def test_glob_truncates(policy: SandboxPolicy) -> None:
    from dir_ai.results import ToolResult

    result = glob_paths(policy, "**/*", max_results=1)
    assert isinstance(result, ToolResult)
    assert result.truncated


# -- registry -----------------------------------------------------------------


def test_registry_builds_six_typed_tools(policy: SandboxPolicy) -> None:
    tools = build_tools(policy, ToolExecutor(policy, AutoApprove()))
    assert [tool.name for tool in tools] == [
        "list_directory_tool",
        "read_file_tool",
        "write_file_tool",
        "edit_file_tool",
        "grep_tool",
        "glob_tool",
    ]
    payload = json.loads(tools[1].invoke({"filename": "app.py"}))
    assert payload["ok"] is True
    assert "return a + b" in payload["output"]
