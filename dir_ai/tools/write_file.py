"""
Tool Layer — write_file tool.
Writes content to a file in the sandboxed working directory.
Always requires human approval before writing.
"""

from langchain.tools import tool

from dir_ai.middleware.approval import request_approval
from dir_ai.tools.sandbox import safe_path


@tool
def write_file_tool(input: str) -> str:
    """
    Writes content to a file in the working directory.
    Input format (use exactly this format):
        FILENAME: <filename>
        CONTENT:
        <file content here>

    Example:
        FILENAME: report.txt
        CONTENT:
        This is the report content.

    Always requires user approval before writing.
    """
    try:
        # Parse the structured input
        if "FILENAME:" not in input or "CONTENT:" not in input:
            return "Invalid input format. Use:\nFILENAME: <name>\nCONTENT:\n<content>"

        lines = input.strip().splitlines()
        filename = ""
        content_lines = []
        in_content = False

        for line in lines:
            if line.startswith("FILENAME:") and not in_content:
                filename = line.replace("FILENAME:", "").strip()
            elif line.startswith("CONTENT:"):
                in_content = True
            elif in_content:
                content_lines.append(line)

        if not filename:
            return "Could not parse filename."

        content = "\n".join(content_lines)
        path = safe_path(filename)

        # Human approval gate
        approved = request_approval(f"Write {len(content)} chars to '{filename}'")
        if not approved:
            return f"Write to '{filename}' was cancelled by the user."

        path.write_text(content, encoding="utf-8")
        return f"Successfully wrote {len(content)} characters to '{filename}'."

    except ValueError as e:
        return str(e)
    except Exception as e:
        return f"Error writing file: {e}"
