"""Tool registry: LangChain tools bound to the approval-aware executor.

The synchronous LangChain tools are a transitional adapter for the legacy CLI.
Every call goes through :class:`dir_ai.execution.ToolExecutor`, so approval
cannot be bypassed.
"""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine

from langchain_core.tools import BaseTool, tool

from dir_ai.results import ToolResult
from dir_ai.sandbox import SandboxPolicy, default_policy


def _run(coroutine: Coroutine[object, object, ToolResult]) -> str:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coroutine).to_json()
    coroutine.close()
    raise RuntimeError("Synchronous LangChain tools cannot run inside an event loop.")


def build_tools(policy: SandboxPolicy, executor: object | None = None) -> list[BaseTool]:
    # Imported lazily to keep the tools package importable on its own.
    from dir_ai.approval import CliApprovalHandler
    from dir_ai.execution import ToolExecutor

    active = executor or ToolExecutor(policy, CliApprovalHandler())
    if not isinstance(active, ToolExecutor):
        raise TypeError("executor must be a ToolExecutor")

    @tool
    def list_directory_tool(path: str = ".", recursive: bool = False) -> str:
        """List files in the workspace. Set recursive=True for a full tree."""
        return _run(active.list_directory(path=path, recursive=recursive))

    @tool
    def read_file_tool(filename: str, offset: int = 0, limit: int = 200) -> str:
        """Read a UTF-8 text file, paged by line.

        Args:
            filename: Path relative to the workspace root.
            offset: Zero-based line to start at.
            limit: Maximum lines to return (1-2000).
        """
        return _run(active.read_file(filename, offset=offset, limit=limit))

    @tool
    def write_file_tool(filename: str, content: str) -> str:
        """Create or overwrite a file with exact content."""
        return _run(active.write_file(filename, content))

    @tool
    def edit_file_tool(filename: str, old: str, new: str) -> str:
        """Replace exactly one occurrence of old with new in a file.

        Fails if the old text is missing or appears more than once.
        """
        return _run(active.edit_file(filename, old, new))

    @tool
    def grep_tool(
        pattern: str, path: str = ".", max_results: int = 100, case_sensitive: bool = True
    ) -> str:
        """Search file contents with a regular expression."""
        return _run(
            active.grep(
                pattern,
                path=path,
                max_results=max_results,
                case_sensitive=case_sensitive,
            )
        )

    @tool
    def glob_tool(pattern: str, path: str = ".", max_results: int = 200) -> str:
        """Find paths matching a glob such as '**/*.py'."""
        return _run(active.glob(pattern, path=path, max_results=max_results))

    return [
        list_directory_tool,
        read_file_tool,
        write_file_tool,
        edit_file_tool,
        grep_tool,
        glob_tool,
    ]


def get_tools() -> list[BaseTool]:
    """Transitional helper for the legacy CLI runner."""
    return build_tools(default_policy())
