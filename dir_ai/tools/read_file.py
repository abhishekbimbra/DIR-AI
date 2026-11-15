"""
Tool Layer — read_file tool.
Reads a file from the sandboxed working directory.
"""

from langchain.tools import tool
from dir_ai.tools.sandbox import safe_path


@tool
def read_file_tool(filename: str) -> str:
    """
    Reads the contents of a file in the working directory.
    Input: filename (e.g., 'main.py' or 'notes.txt').
    Do NOT include path separators or parent directory references.
    """
    try:
        path = safe_path(filename)
        if not path.exists():
            return f"File not found: '{filename}'"
        if not path.is_file():
            return f"'{filename}' is not a file."
        content = path.read_text(encoding="utf-8", errors="replace")
        # Cap at 4000 chars to stay within context limits
        if len(content) > 4000:
            return content[:4000] + "\n\n[...content truncated at 4000 chars...]"
        return content
    except ValueError as e:
        return str(e)
    except Exception as e:
        return f"Error reading file: {e}"
