"""Baseline: no defense at all."""

from __future__ import annotations

from arena.defenses.base import Defense


class NoDefense(Defense):
    """Lets every tool call through unchanged."""

    name = "none"
    version = "1"
