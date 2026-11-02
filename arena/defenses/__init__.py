"""Defense interface, built-in baselines and adapters for third-party defenses."""

from __future__ import annotations

from collections.abc import Callable

from arena.defenses.base import (
    Allow,
    Confirm,
    Decision,
    Defense,
    DefenseContext,
    Deny,
    ToolCall,
    ToolEvent,
    ToolResult,
)
from arena.defenses.none import NoDefense
from arena.defenses.prompt_hardening import PromptHardeningDefense
from arena.defenses.reference_taint import ReferenceTaintDefense

DEFENSES: dict[str, Callable[[], Defense]] = {
    NoDefense.name: NoDefense,
    PromptHardeningDefense.name: PromptHardeningDefense,
    ReferenceTaintDefense.name: ReferenceTaintDefense,
}
"""Registry of defenses by name. Each value builds a fresh instance for one run."""


def get_defense(name: str) -> Defense:
    """Return a new instance of the defense called ``name``."""
    try:
        return DEFENSES[name]()
    except KeyError:
        raise ValueError(f"unknown defense {name!r}; available: {sorted(DEFENSES)}") from None


__all__ = [
    "DEFENSES",
    "Allow",
    "Confirm",
    "Decision",
    "Defense",
    "DefenseContext",
    "Deny",
    "NoDefense",
    "PromptHardeningDefense",
    "ReferenceTaintDefense",
    "ToolCall",
    "ToolEvent",
    "ToolResult",
    "get_defense",
]
