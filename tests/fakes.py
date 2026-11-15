"""Test-only fakes. Imported by unit and integration tests."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field, PrivateAttr


class FakeToolChatModel(BaseChatModel):
    """Replays scripted AIMessages and records what it was sent.

    Supports ``bind_tools`` by returning itself, which is enough for the agent
    loop: the scripted responses already contain the tool calls under test.
    """

    responses: list[AIMessage] = Field(default_factory=list)
    calls: list[list[BaseMessage]] = Field(default_factory=list)
    bound_tool_names: list[str] = Field(default_factory=list)
    _cursor: int = PrivateAttr(default=0)

    @property
    def _llm_type(self) -> str:
        return "fake-tool-chat-model"

    def bind_tools(self, tools: Sequence[Any], **kwargs: Any) -> FakeToolChatModel:
        self.bound_tool_names = [
            getattr(tool, "name", None) or getattr(tool, "__name__", "unknown") for tool in tools
        ]
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        self.calls.append(list(messages))
        if self._cursor >= len(self.responses):
            raise AssertionError(
                f"FakeToolChatModel exhausted after {len(self.responses)} response(s); "
                f"call #{self._cursor + 1} was unexpected."
            )
        message = self.responses[self._cursor]
        self._cursor += 1
        return ChatResult(generations=[ChatGeneration(message=message)])

    @property
    def remaining(self) -> int:
        return len(self.responses) - self._cursor
