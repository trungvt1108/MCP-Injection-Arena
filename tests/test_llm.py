import sys
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

from arena.agent.llm import AssistantTurn, LiteLLMClient, parse_arguments
from arena.agent.mock_llm import ScriptedLLM, answer
from arena.defenses import ToolCall
from arena.scenarios.schema import MockAnswerStep, MockToolStep

pytestmark = pytest.mark.anyio


def test_parse_arguments() -> None:
    assert parse_arguments('{"a": 1}') == {"a": 1}
    assert parse_arguments("") == {}
    assert parse_arguments(None) == {}
    assert parse_arguments("{not json") == {"_raw": "{not json"}
    assert parse_arguments("[1, 2]") == {"_raw": "[1, 2]"}


def test_assistant_turn_to_message() -> None:
    turn = AssistantTurn(content="hi", tool_calls=(ToolCall("c1", "read_file", {"path": "x"}),))
    assert turn.to_message() == {
        "role": "assistant",
        "content": "hi",
        "tool_calls": [
            {
                "id": "c1",
                "type": "function",
                "function": {"name": "read_file", "arguments": '{"path": "x"}'},
            }
        ],
    }
    assert AssistantTurn(content="bye").to_message() == {"role": "assistant", "content": "bye"}


async def test_litellm_client_with_fake_module(monkeypatch: pytest.MonkeyPatch) -> None:
    """The adapter's request and response handling, with LiteLLM replaced by a fake."""
    captured: dict[str, Any] = {}

    async def acompletion(**kwargs: Any) -> Any:
        captured.update(kwargs)
        tc = SimpleNamespace(
            id="abc", function=SimpleNamespace(name="read_file", arguments='{"path": ".env"}')
        )
        message = SimpleNamespace(content=None, tool_calls=[tc])
        usage = SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=usage)

    fake = ModuleType("litellm")
    fake.acompletion = acompletion  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "litellm", fake)
    monkeypatch.delenv("LITELLM_LOCAL_MODEL_COST_MAP", raising=False)

    client = LiteLLMClient("ollama/llama3.1", seed=42)
    turn = await client.complete([{"role": "user", "content": "hi"}], [{"type": "function"}])

    assert turn.tool_calls == (ToolCall("abc", "read_file", {"path": ".env"}),)
    assert turn.usage == {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
    assert captured["model"] == "ollama/llama3.1"
    assert captured["temperature"] == 0.0
    assert captured["seed"] == 42
    assert captured["drop_params"] is True
    import os

    assert os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] == "True"


async def test_scripted_llm_exhaustion_and_recording() -> None:
    llm = ScriptedLLM([answer("one")])
    assert (await llm.complete([{"role": "user", "content": "q"}], [])).content == "one"
    assert (await llm.complete([], [])).content == ""
    assert len(llm.calls) == 2
    assert llm.calls[0][0] == [{"role": "user", "content": "q"}]


async def test_scripted_llm_from_trajectory() -> None:
    llm = ScriptedLLM.from_trajectory(
        [
            MockToolStep(tool="http_post", arguments={"body": "k={{ canary.key }}", "n": 1}),
            MockAnswerStep(answer="sent {{ canary.key }}"),
        ],
        {"canary.key": "SECRET"},
    )
    first = await llm.complete([], [])
    assert first.tool_calls[0].name == "http_post"
    assert first.tool_calls[0].arguments == {"body": "k=SECRET", "n": 1}
    assert (await llm.complete([], [])).content == "sent SECRET"
