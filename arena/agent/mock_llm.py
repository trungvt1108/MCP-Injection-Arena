"""A scripted LLM for deterministic, offline tests.

Each step is either a fixed :class:`AssistantTurn` or a function of the
conversation so far. The function form lets a test model a compromised agent
that really copies data out of a tool result.
"""

from __future__ import annotations

import itertools
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from arena.agent.llm import AssistantTurn, Message
from arena.defenses.base import ToolCall
from arena.scenarios.environment import substitute
from arena.scenarios.schema import MockAnswerStep, MockStep, MockToolStep

Step = AssistantTurn | Callable[[Sequence[Message]], AssistantTurn]

_ids = itertools.count(1)


def tool_call(name: str, **arguments: Any) -> AssistantTurn:
    """A turn that calls one tool."""
    return AssistantTurn(
        content=None, tool_calls=(ToolCall(f"call_{next(_ids)}", name, arguments),)
    )


def answer(text: str) -> AssistantTurn:
    """A turn with a final answer and no tool calls."""
    return AssistantTurn(content=text)


def last_tool_output(messages: Sequence[Message]) -> str:
    """Return the content of the most recent tool message."""
    for message in reversed(messages):
        if message.get("role") == "tool":
            return str(message.get("content", ""))
    return ""


class ScriptedLLM:
    """Plays back a fixed list of steps. When the script runs out, it gives an empty answer."""

    def __init__(self, steps: Sequence[Step], *, name: str = "mock") -> None:
        """Create a mock that will return ``steps`` in order."""
        self._steps = list(steps)
        self._name = name
        self.calls: list[tuple[list[Message], list[dict[str, Any]]]] = []
        """Every request received: (messages, tools). For assertions in tests."""

    @property
    def name(self) -> str:
        """Model name recorded in results."""
        return self._name

    async def complete(self, messages: list[Message], tools: list[dict[str, Any]]) -> AssistantTurn:
        """Return the next scripted turn."""
        self.calls.append(([dict(m) for m in messages], tools))
        if len(self.calls) > len(self._steps):
            return answer("")
        step = self._steps[len(self.calls) - 1]
        return step(messages) if callable(step) else step

    @classmethod
    def from_trajectory(
        cls, steps: Sequence[MockStep], substitutions: Mapping[str, str]
    ) -> ScriptedLLM:
        """Build a mock from a scenario's ``mock_trajectory``, with placeholders filled."""
        turns: list[Step] = []
        for i, step in enumerate(steps, start=1):
            match step:
                case MockToolStep():
                    args = substitute(dict(step.arguments), dict(substitutions))
                    turns.append(
                        AssistantTurn(
                            content=None, tool_calls=(ToolCall(f"call_{i}", step.tool, args),)
                        )
                    )
                case MockAnswerStep():
                    turns.append(answer(substitute(step.answer, dict(substitutions))))
        return cls(turns)
