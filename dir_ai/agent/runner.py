"""
Agent Layer — LangChain ReAct agent powered by Gemini.
Compatible with LangChain v0.3.x
"""

# ── LangChain v0.3.x imports (all moved to langchain_core / langchain package)
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_classic.agents import create_react_agent
from langchain_classic.agents import AgentExecutor
from langchain_core.prompts import PromptTemplate

from dir_ai.tools.registry import get_tools
from dir_ai.middleware.callbacks import DirAICallbackHandler
from dir_ai.config import GEMINI_API_KEY, GEMINI_MODEL



# ── ReAct prompt template (inline — no hub.pull() needed, avoids network call)
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


def build_agent() -> AgentExecutor:
    llm = ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        google_api_key=GEMINI_API_KEY,
        temperature=0.2,
    )

    tools = get_tools()

    agent = create_react_agent(
        llm=llm,
        tools=tools,
        prompt=REACT_PROMPT,
    )

    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=False,               # We handle output via our callback
        handle_parsing_errors=True,
        max_iterations=10,
        callbacks=[DirAICallbackHandler()],
    )


# Build once, reuse across session
_agent_executor = None


def run_agent(user_input: str):
    global _agent_executor

    from dir_ai.ui.renderer import print_planning

    if _agent_executor is None:
        _agent_executor = build_agent()

    print_planning()
    _agent_executor.invoke({"input": user_input})