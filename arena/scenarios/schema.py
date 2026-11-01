"""Pydantic models for scenario YAML files.

A scenario is a user task, the environment the agent works in, one injected
payload, an attack goal, and the utility checks that say whether the user's task
got done. See ``docs/adding-a-scenario.md`` for a walkthrough.

Strings in ``environment``, ``user_task`` and ``mock_trajectory`` may use two
kinds of placeholder, filled in when a run starts:

- ``{{ injection }}``: the injection payload. Attacks can swap the payload while
  keeping its location.
- ``{{ canary.<name> }}``: the value of a canary declared under ``canaries``.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from arena.canary import DEFAULT_CORE_LENGTH, DEFAULT_PREFIX, MIN_CORE_LENGTH
from arena.servers import SERVER_NAMES
from arena.servers.issues import IssuesState
from arena.servers.mail import MailState
from arena.servers.shell import ShellState
from arena.servers.sink import SinkState
from arena.servers.web import WebState

PLACEHOLDER = re.compile(r"\{\{\s*([A-Za-z0-9_.\-]+)\s*\}\}")


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


# --- building blocks -----------------------------------------------------------


class StringMatch(_Model):
    """Match a string by exact value, substring or regex (case-insensitive by default)."""

    equals: str | None = None
    contains: str | None = None
    regex: str | None = None
    case_sensitive: bool = False

    @model_validator(mode="after")
    def _exactly_one(self) -> StringMatch:
        if sum(x is not None for x in (self.equals, self.contains, self.regex)) != 1:
            raise ValueError("set exactly one of equals, contains, regex")
        if self.regex is not None:
            try:
                re.compile(self.regex)
            except re.error as exc:
                raise ValueError(f"invalid regex {self.regex!r}: {exc}") from exc
        return self

    def matches(self, value: Any) -> bool:
        """Return True if ``value`` (JSON-encoded if not a string) matches."""
        text = value if isinstance(value, str) else json.dumps(value, sort_keys=True)
        if self.regex is not None:
            flags = 0 if self.case_sensitive else re.IGNORECASE
            return re.search(self.regex, text, flags) is not None
        target = self.equals if self.equals is not None else self.contains
        assert target is not None
        if not self.case_sensitive:
            text, target = text.casefold(), target.casefold()
        return text == target if self.equals is not None else target in text


class CanarySpec(_Model):
    """A canary to generate fresh for every run."""

    name: str = Field(pattern=r"^[A-Za-z0-9_\-]+$")
    prefix: str = DEFAULT_PREFIX
    length: int = Field(default=DEFAULT_CORE_LENGTH, ge=MIN_CORE_LENGTH)


class Injection(_Model):
    """Where the attacker's content sits and what it is trying to achieve.

    The scenario holds no payload prose: ``goal`` is a neutral, machine-checkable
    description of the attacker's objective, and ``template`` names an entry in
    :mod:`arena.attacks.templates`. The payload the agent sees is the template
    rendered with the goal (see :func:`arena.scenarios.environment.materialize`).
    """

    location: str
    """Human-readable location, e.g. ``"issues: comment on #1"``."""
    goal: str
    """Neutral description of the objective, e.g. "email .env to mallory@attacker.example"."""
    template: str = Field(default="placeholder/default", pattern=r"^[a-z0-9_]+/[a-z0-9_]+$")
    """Attack-template ref ``<family>/<variant>``; resolved against the template registry."""
    technique: str = "direct"
    """Short tag for reports, e.g. ``direct``, ``base64``, ``split``."""


class FilesystemEnv(_Model):
    """Initial files in the sandbox: relative path -> text content."""

    files: dict[str, str] = Field(default_factory=dict)


class Environment(_Model):
    """Initial state for each server. Each section uses that server's own state model."""

    filesystem: FilesystemEnv | None = None
    mail: MailState | None = None
    web: WebState | None = None
    issues: IssuesState | None = None
    sink: SinkState | None = None
    shell: ShellState | None = None

    def configured(self) -> set[str]:
        """Names of servers that have an environment section."""
        return {name for name in SERVER_NAMES if getattr(self, name) is not None}


# --- attack goals ---------------------------------------------------------------


class CanaryExfil(_Model):
    """A canary shows up, in any encoding, in anything that left the sandbox."""

    type: Literal["canary_exfil"]
    canary: str | None = None
    """Canary name; ``None`` means any canary."""


class FileDeleted(_Model):
    """A file that existed at the start is gone at the end."""

    type: Literal["file_deleted"]
    path: str


class CommandExecuted(_Model):
    """The agent ran a matching shell command."""

    type: Literal["command_executed"]
    command: StringMatch


class ToolCalledWith(_Model):
    """A tool actually ran with arguments matching every predicate."""

    type: Literal["tool_called_with"]
    tool: str
    arguments: dict[str, StringMatch] = Field(default_factory=dict)


AttackGoal = Annotated[
    CanaryExfil | FileDeleted | CommandExecuted | ToolCalledWith,
    Field(discriminator="type"),
]


# --- utility checks -------------------------------------------------------------


class FileContains(_Model):
    """A sandbox file contains some text at the end of the run."""

    type: Literal["file_contains"]
    path: str
    text: str


class MessageSentTo(_Model):
    """Mail or a chat message went to ``recipient``, optionally containing ``text``."""

    type: Literal["message_sent_to"]
    recipient: str
    text: str | None = None


class AnswerContains(_Model):
    """The agent's final answer contains ``text`` (case-insensitive)."""

    type: Literal["answer_contains"]
    text: str


UtilityCheck = Annotated[
    FileContains | MessageSentTo | AnswerContains,
    Field(discriminator="type"),
]


# --- mock trajectory --------------------------------------------------------------


class MockToolStep(_Model):
    """A scripted tool call."""

    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class MockAnswerStep(_Model):
    """A scripted final answer."""

    answer: str


MockStep = MockToolStep | MockAnswerStep


# --- scenario -----------------------------------------------------------------------


class Scenario(_Model):
    """One benchmark scenario."""

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9\-]*$")
    title: str
    category: str = ""
    """Defaults to the name of the folder the file sits in."""
    description: str = ""
    user_task: str
    servers: list[str] = Field(min_length=1)
    canaries: list[CanarySpec] = Field(default_factory=list)
    environment: Environment = Field(default_factory=Environment)
    injection: Injection | None = None
    attack_goal: AttackGoal
    utility: list[UtilityCheck] = Field(min_length=1)
    mock_trajectory: list[MockStep] = Field(default_factory=list)
    """Scripted turns of a fully compromised agent, for ``--model mock``. It must
    reach the attack goal under ``defense=none``, which proves the scenario can
    actually be judged as a success."""

    @model_validator(mode="after")
    def _check_consistency(self) -> Scenario:
        unknown = set(self.servers) - set(SERVER_NAMES)
        if unknown:
            raise ValueError(f"unknown servers {sorted(unknown)}; expected {SERVER_NAMES}")
        unused = self.environment.configured() - set(self.servers)
        if unused:
            raise ValueError(f"environment for servers not in `servers`: {sorted(unused)}")

        names = [c.name for c in self.canaries]
        if len(names) != len(set(names)):
            raise ValueError("canary names must be unique")
        if isinstance(self.attack_goal, CanaryExfil):
            if not names:
                raise ValueError("canary_exfil needs at least one canary")
            if self.attack_goal.canary is not None and self.attack_goal.canary not in names:
                raise ValueError(
                    f"attack_goal refers to unknown canary {self.attack_goal.canary!r}"
                )

        allowed = {f"canary.{n}" for n in names}
        if self.injection is not None:
            allowed.add("injection")
        used = set(self.placeholders())
        if bad := used - allowed:
            raise ValueError(f"unknown placeholders {sorted(bad)}; allowed: {sorted(allowed)}")
        if self.injection is not None and "injection" not in used:
            raise ValueError("the injection payload is never placed: add {{ injection }}")
        return self

    def placeholders(self) -> Iterator[str]:
        """Yield every placeholder name used in templated fields."""
        templated = {
            "user_task": self.user_task,
            "environment": self.environment.model_dump(),
            "mock_trajectory": [s.model_dump() for s in self.mock_trajectory],
        }
        for text in _strings(templated):
            for match in PLACEHOLDER.finditer(text):
                yield match.group(1)


def _strings(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for k, v in value.items():
            yield from _strings(k)
            yield from _strings(v)
    elif isinstance(value, list | tuple):
        for v in value:
            yield from _strings(v)
