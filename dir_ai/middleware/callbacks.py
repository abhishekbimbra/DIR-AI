"""
Middleware Layer — LangChain callback handler.
Intercepts agent reasoning steps and renders them via the UI layer.
"""

from typing import Any, Union
from langchain_classic.callbacks.base import BaseCallbackHandler
from langchain_core.agents import AgentAction, AgentFinish

from dir_ai.ui.renderer import (
    print_thought,
    print_action,
    print_observation,
    print_final_answer,
)


class DirAICallbackHandler(BaseCallbackHandler):

    def on_agent_action(self, action: AgentAction, **kwargs: Any):
        """Called when the agent decides on an action."""
        # AgentAction.log contains the full Thought + Action text
        log = action.log.strip()
        # Parse out the Thought line if present
        for line in log.splitlines():
            line = line.strip()
            if line.startswith("Thought:"):
                print_thought(line.replace("Thought:", "").strip())
                break
        print_action(action.tool)

    def on_tool_end(self, output: str, **kwargs: Any):
        """Called after a tool returns its result."""
        preview = output[:300] + "..." if len(output) > 300 else output
        print_observation(preview)

    def on_agent_finish(self, finish: AgentFinish, **kwargs: Any):
        """Called when the agent produces its final answer."""
        output = finish.return_values.get("output", "")
        print_final_answer(output)
