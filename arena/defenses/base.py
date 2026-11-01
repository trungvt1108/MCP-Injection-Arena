"""The Defense interface.

A defense can act at two levels, and may use both:

1. **Proxy level**: :meth:`Defense.wrap_server` rewrites how each MCP server is
   launched, e.g. to put a filtering proxy process in front of it. Such a defense
   sees only MCP traffic.
2. **In-process hooks**: :meth:`Defense.on_tool_call` decides whether a tool call
   may run (:class:`Allow`, :class:`Deny` or :class:`Confirm`).
   :meth:`Defense.on_tool_result` may rewrite what the model sees.
   :meth:`Defense.system_prompt` may rewrite the system prompt.

A fresh instance is created for every run, so defenses may keep per-run state
(e.g. a taint set) on ``self``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, Literal

from mcp import StdioServerParameters


@dataclass(frozen=True)
class ToolCall:
    """A tool call requested by the model."""

    id: str
    name: str
    arguments: dict[str, Any]
    server: str = ""
    """Name of the mock server that owns the tool (filled in by the runner)."""


@dataclass(frozen=True)
class ToolResult:
    """The result of a tool call, as the model will see it."""

    call: ToolCall
    text: str
    is_error: bool = False


@dataclass(frozen=True)
class Allow:
    """Let the tool call run."""


@dataclass(frozen=True)
class Deny:
    """Block the tool call. ``reason`` is shown to the model."""

    reason: str


@dataclass(frozen=True)
class Confirm:
    """Ask the (simulated) user. ``reason`` is what the user would be shown."""

    reason: str


Decision = Allow | Deny | Confirm

DecisionLabel = Literal["allow", "deny", "confirm_approved", "confirm_declined"]


@dataclass
class ToolEvent:
    """One tool call, the decision taken on it, and its result if it ran."""

    call: ToolCall
    decision: DecisionLabel
    reason: str = ""
    result: ToolResult | None = None

    @property
    def executed(self) -> bool:
        """Whether the call actually reached the server."""
        return self.decision in ("allow", "confirm_approved")


@dataclass
class DefenseContext:
    """What a defense may know about the run in progress."""

    scenario_id: str
    user_task: str
    tool_names: dict[str, str] = field(default_factory=dict)
    """Tool name -> server name for every tool offered to the model."""
    history: list[ToolEvent] = field(default_factory=list)
    """Earlier tool events of this run, oldest first."""


class Defense:
    """Base class for all defenses. The default behavior is to do nothing."""

    name: ClassVar[str] = "base"
    version: ClassVar[str] = "0"

    def system_prompt(self, prompt: str) -> str:
        """Return the system prompt to use instead of ``prompt``."""
        return prompt

    def wrap_server(self, params: StdioServerParameters) -> StdioServerParameters:
        """Return how to launch a server, e.g. behind a proxy process."""
        return params

    async def on_tool_call(self, call: ToolCall, ctx: DefenseContext) -> Decision:
        """Decide whether ``call`` may run."""
        return Allow()

    async def on_tool_result(self, result: ToolResult, ctx: DefenseContext) -> ToolResult:
        """Return the result the model should see in place of ``result``."""
        return result

    async def close(self) -> None:
        """Release any resources held by the defense."""
