"""Tool registry: builds LangChain tools bound to a sandbox policy."""

from __future__ import annotations

from langchain_core.tools import BaseTool, tool

from dir_ai.sandbox import SandboxPolicy, default_policy
from dir_ai.tools.edit_file import edit_file
from dir_ai.tools.glob import glob_paths
from dir_ai.tools.grep import grep
from dir_ai.tools.list_directory import list_directory
from dir_ai.tools.read_file import read_file
from dir_ai.tools.write_file import write_file


def build_tools(policy: SandboxPolicy) -> list[BaseTool]:
    @tool
    def list_directory_tool(path: str = ".", recursive: bool = False) -> str:
        """List files in the workspace. Set recursive=True for a full tree."""
        return list_directory(policy, path=path, recursive=recursive).to_json()

    @tool
    def read_file_tool(filename: str, offset: int = 0, limit: int = 200) -> str:
        """Read a UTF-8 text file, paged by line.

        Args:
            filename: Path relative to the workspace root.
            offset: Zero-based line to start at.
            limit: Maximum lines to return (1-2000).
        """
        return read_file(policy, filename, offset=offset, limit=limit).to_json()

    @tool
    def write_file_tool(filename: str, content: str) -> str:
        """Create or overwrite a file with exact content."""
        return write_file(policy, filename, content).to_json()

    @tool
    def edit_file_tool(filename: str, old: str, new: str) -> str:
        """Replace exactly one occurrence of old with new in a file.

        Fails if the old text is missing or appears more than once.
        """
        return edit_file(policy, filename, old, new).to_json()

    @tool
    def grep_tool(
        pattern: str, path: str = ".", max_results: int = 100, case_sensitive: bool = True
    ) -> str:
        """Search file contents with a regular expression."""
        return grep(
            policy,
            pattern,
            path=path,
            max_results=max_results,
            case_sensitive=case_sensitive,
        ).to_json()

    @tool
    def glob_tool(pattern: str, path: str = ".", max_results: int = 200) -> str:
        """Find paths matching a glob such as '**/*.py'."""
        return glob_paths(policy, pattern, path=path, max_results=max_results).to_json()

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
