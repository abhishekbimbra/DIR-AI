from __future__ import annotations

import ast
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[2] / "dir_ai"
SANDBOX = "sandbox.py"

FORBIDDEN_NAMES = {"open"}
FORBIDDEN_OS_FUNCS = {
    "listdir",
    "scandir",
    "walk",
    "remove",
    "unlink",
    "rename",
    "replace",
    "makedirs",
    "mkdir",
    "rmdir",
    "stat",
}
FORBIDDEN_METHODS = {
    "read_text",
    "write_text",
    "read_bytes",
    "write_bytes",
    "iterdir",
    "rglob",
    "glob",
    "open",
    "unlink",
    "mkdir",
}
ALLOWED_RECEIVERS = {"policy", "self"}


def _violations(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in {"shutil"}:
                    found.append(f"{path.name}:{node.lineno}: import {alias.name}")
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module.split(".")[0] in {"shutil"}:
                found.append(f"{path.name}:{node.lineno}: from {node.module} import")
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in FORBIDDEN_NAMES:
                found.append(f"{path.name}:{node.lineno}: {func.id}()")
            elif isinstance(func, ast.Attribute):
                receiver = func.value
                receiver_name = receiver.id if isinstance(receiver, ast.Name) else None
                if receiver_name == "os" and func.attr in FORBIDDEN_OS_FUNCS:
                    found.append(f"{path.name}:{node.lineno}: os.{func.attr}()")
                elif func.attr in FORBIDDEN_METHODS and receiver_name not in ALLOWED_RECEIVERS:
                    found.append(f"{path.name}:{node.lineno}: .{func.attr}()")
    return found


def test_no_raw_file_io_outside_sandbox() -> None:
    violations: list[str] = []
    for path in sorted(PACKAGE.rglob("*.py")):
        if path.name == SANDBOX:
            continue
        violations.extend(_violations(path))
    assert violations == [], "\n".join(violations)
