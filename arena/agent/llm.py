"""The LLM interface used by the agent loop, and its LiteLLM implementation.

Messages and tools use the OpenAI chat-completions format, which LiteLLM
translates for every provider (OpenAI, Anthropic, Gemini, Ollama, ...).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Protocol

from arena.defenses.base import ToolCall

Message = dict[str, Any]
"""One chat message in OpenAI format."""


@dataclass(frozen=True)
class AssistantTurn:
    """What the model said in one step: text, tool calls, or both."""

    content: str | None
    tool_calls: tuple[ToolCall, ...] = ()
    usage: dict[str, int] = field(default_factory=dict)

    def to_message(self) -> Message:
        """Render this turn as an OpenAI-format assistant message."""
        message: Message = {"role": "assistant", "content": self.content}
        if self.tool_calls:
            message["tool_calls"] = [
                {
                    "id": c.id,
                    "type": "function",
                    "function": {"name": c.name, "arguments": json.dumps(c.arguments)},
                }
                for c in self.tool_calls
            ]
        return message


class LLM(Protocol):
    """Anything that can produce the next assistant turn."""

    @property
    def name(self) -> str:
        """Model identifier recorded in results."""
        ...

    async def complete(self, messages: list[Message], tools: list[dict[str, Any]]) -> AssistantTurn:
        """Return the next assistant turn for ``messages``."""
        ...


def parse_arguments(raw: str | None) -> dict[str, Any]:
    """Parse a tool-call argument string. Malformed JSON is kept under ``_raw``."""
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {"_raw": raw}
    return parsed if isinstance(parsed, dict) else {"_raw": raw}


class LiteLLMClient:
    """Calls any LiteLLM-supported model, deterministically where the provider allows."""

    def __init__(
        self,
        model: str,
        *,
        temperature: float = 0.0,
        seed: int | None = None,
        max_tokens: int | None = None,
        timeout: float = 120.0,
        num_retries: int = 2,
    ) -> None:
        """Configure the client. Nothing is contacted until :meth:`complete`."""
        self.model = model
        self.temperature = temperature
        self.seed = seed
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.num_retries = num_retries

    @property
    def name(self) -> str:
        """The LiteLLM model string, e.g. ``ollama/llama3.1``."""
        return self.model

    async def complete(self, messages: list[Message], tools: list[dict[str, Any]]) -> AssistantTurn:
        """Request one completion and convert it to an :class:`AssistantTurn`."""
        # LiteLLM downloads a model price list from the internet on import unless
        # told to use its bundled copy. The arena never needs the live one.
        os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")
        import litellm  # imported lazily: slow, and only needed for real models

        response: Any = await litellm.acompletion(
            model=self.model,
            messages=messages,
            tools=tools or None,
            temperature=self.temperature,
            seed=self.seed,
            max_tokens=self.max_tokens,
            timeout=self.timeout,
            num_retries=self.num_retries,
            drop_params=True,  # e.g. providers that do not support `seed`
        )
        message = response.choices[0].message
        calls = tuple(
            ToolCall(
                id=tc.id or f"call_{i}",
                name=tc.function.name or "",
                arguments=parse_arguments(tc.function.arguments),
            )
            for i, tc in enumerate(message.tool_calls or [])
        )
        usage = getattr(response, "usage", None)
        tokens = {
            k: int(getattr(usage, k, 0) or 0)
            for k in ("prompt_tokens", "completion_tokens", "total_tokens")
        }
        return AssistantTurn(content=message.content, tool_calls=calls, usage=tokens)
