"""
Tool Layer — Registry that assembles all sandboxed tools for the agent.
"""

from langchain_core.tools import BaseTool

from dir_ai.tools.list_directory import list_directory_tool
from dir_ai.tools.read_file import read_file_tool
from dir_ai.tools.write_file import write_file_tool


def get_tools() -> list[BaseTool]:
    return [
        list_directory_tool,
        read_file_tool,
        write_file_tool,
    ]
