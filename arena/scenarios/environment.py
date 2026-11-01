"""Turn a scenario into concrete server state in a fresh state directory."""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from arena.canary import Canary, generate_canary
from arena.scenarios.schema import PLACEHOLDER, Scenario
from arena.servers import filesystem, issues, mail, shell, sink, web
from arena.servers._state import ServerState, StateStore


@dataclass(frozen=True)
class Materialized:
    """What a run needs to know about the environment it was given."""

    state_dir: Path
    canaries: dict[str, Canary]
    substitutions: dict[str, str]
    initial_files: dict[str, bytes]


def substitute(value: Any, substitutions: dict[str, str]) -> Any:
    """Replace ``{{ name }}`` placeholders in every string inside ``value``.

    Substitution happens in one pass, so a payload that itself contains ``{{ ... }}``
    is inserted literally and never expanded.
    """
    if isinstance(value, str):
        return PLACEHOLDER.sub(lambda m: substitutions[m.group(1)], value)
    if isinstance(value, dict):
        return {
            substitute(k, substitutions): substitute(v, substitutions) for k, v in value.items()
        }
    if isinstance(value, list):
        return [substitute(v, substitutions) for v in value]
    return value


def materialize(
    scenario: Scenario,
    state_dir: Path,
    rng: random.Random,
    *,
    payload: str | None = None,
) -> Materialized:
    """Generate canaries, fill placeholders and seed every server's state.

    Args:
        scenario: The scenario to set up.
        state_dir: Empty directory that will hold all server state.
        rng: Seeded randomness (canary values are drawn from it).
        payload: Replaces the scenario's own injection payload (used by attacks).
    """
    canaries = {
        spec.name: generate_canary(prefix=spec.prefix, length=spec.length, label=spec.name, rng=rng)
        for spec in scenario.canaries
    }
    subs = {f"canary.{name}": c.value for name, c in canaries.items()}
    if scenario.injection is not None:
        subs["injection"] = payload if payload is not None else scenario.injection.payload

    env = scenario.environment
    state_dir.mkdir(parents=True, exist_ok=True)
    if "filesystem" in scenario.servers:
        files = env.filesystem.files if env.filesystem else {}
        filesystem.seed(state_dir, substitute(dict(files), subs))

    stores: dict[str, tuple[ServerState | None, StateStore[Any]]] = {
        "mail": (env.mail, mail.store(state_dir)),
        "web": (env.web, web.store(state_dir)),
        "issues": (env.issues, issues.store(state_dir)),
        "sink": (env.sink, sink.store(state_dir)),
        "shell": (env.shell, shell.store(state_dir)),
    }
    for name, (state, store) in stores.items():
        if name in scenario.servers and state is not None:
            data = substitute(state.model_dump(mode="json"), subs)
            store.save(store.model.model_validate(data))

    return Materialized(
        state_dir=state_dir,
        canaries=canaries,
        substitutions=subs,
        initial_files=filesystem.snapshot(state_dir),
    )
