"""
Tool Layer — list_directory tool.
Lists all files in the sandboxed working directory.
"""

from langchain.tools import tool

from dir_ai.tools.sandbox import BASE_DIR


@tool
def list_directory_tool(input: str = "") -> str:
    """
    Lists all files and folders in the current working directory.
    Use this to discover what files are available before reading or writing.
    Input is ignored — pass an empty string.
    """
    try:
        entries = sorted(BASE_DIR.iterdir())
        if not entries:
            return "The working directory is empty."
        lines = []
        for entry in entries:
            tag = "[DIR]" if entry.is_dir() else "[FILE]"
            lines.append(f"{tag} {entry.name}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error listing directory: {e}"
