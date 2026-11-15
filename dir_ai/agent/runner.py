"""Agent layer — transitional LangChain ReAct implementation.

This module is replaced by the native tool-calling loop in CP6. Until then it
keeps the CLI usable while the typed event stream and tools are rebuilt.
"""

from __future__ import annotations

from langchain_classic.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from dir_ai.config import ConfigError, Settings
from dir_ai.middleware.callbacks import DirAICallbackHandler
from dir_ai.tools.registry import get_tools

REACT_TEMPLATE = """Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought:{agent_scratchpad}"""

REACT_PROMPT = PromptTemplate.from_template(REACT_TEMPLATE)

_agent_executor: AgentExecutor | None = None


def build_agent(settings: Settings) -> AgentExecutor:
    if settings.provider != "gemini":
        raise ConfigError("The transitional CLI agent supports only the gemini provider.")
    if not settings.google_api_key:
        raise ConfigError("GOOGLE_API_KEY is required for the gemini provider.")

    llm = ChatGoogleGenerativeAI(
        model=settings.model,
        google_api_key=settings.google_api_key,
        temperature=settings.temperature,
        timeout=settings.timeout,
    )
    tools = get_tools()
    agent = create_react_agent(llm=llm, tools=tools, prompt=REACT_PROMPT)
    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=False,
        handle_parsing_errors=True,
        max_iterations=settings.max_iterations,
        callbacks=[DirAICallbackHandler()],
    )


def run_agent(user_input: str, settings: Settings) -> None:
    global _agent_executor
    from dir_ai.ui.renderer import print_planning

    if _agent_executor is None:
        _agent_executor = build_agent(settings)

    print_planning()
    _agent_executor.invoke({"input": user_input})
