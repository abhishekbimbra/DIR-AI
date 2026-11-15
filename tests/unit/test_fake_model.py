from __future__ import annotations

from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from tests.fakes import FakeToolChatModel


def test_replays_scripted_messages() -> None:
    model = FakeToolChatModel(responses=[AIMessage(content="first"), AIMessage(content="second")])

    assert model.invoke([HumanMessage(content="hello")]).content == "first"
    assert model.invoke([HumanMessage(content="again")]).content == "second"
    assert len(model.calls) == 2
    assert model.calls[0][0].content == "hello"
    assert model.remaining == 0


def test_exhaustion_is_loud() -> None:
    model = FakeToolChatModel(responses=[])
    with pytest.raises(AssertionError, match="exhausted"):
        model.invoke([HumanMessage(content="hello")])


def test_bind_tools_records_names() -> None:
    model = FakeToolChatModel(responses=[AIMessage(content="ok")])
    tool = SimpleNamespace(name="read_file")
    assert model.bind_tools([tool]) is model
    assert model.bound_tool_names == ["read_file"]


def test_tool_call_message_round_trips() -> None:
    message = AIMessage(
        content="",
        tool_calls=[{"name": "read_file", "args": {"filename": "a.py"}, "id": "call-1"}],
    )
    model = FakeToolChatModel(responses=[message])
    result = model.invoke([HumanMessage(content="read it")])
    assert result.tool_calls[0]["id"] == "call-1"
