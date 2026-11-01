"""Load and validate scenario YAML files."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import yaml
from pydantic import ValidationError

from arena.scenarios.schema import Scenario

DATA_DIR = Path(__file__).parent / "data"
"""Built-in scenarios. Each sub-folder is a category."""


class ScenarioError(ValueError):
    """A scenario file is malformed or two scenarios share an id."""


def load_scenario_file(path: Path, *, root: Path | None = None) -> Scenario:
    """Load one scenario file. ``category`` defaults to its folder relative to ``root``."""
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ScenarioError(f"{path}: invalid YAML: {exc}") from exc
    if not isinstance(raw, dict):
        raise ScenarioError(f"{path}: expected a mapping at the top level")
    if not raw.get("category") and root is not None and path.parent != root:
        raw["category"] = path.parent.relative_to(root).as_posix()
    try:
        return Scenario.model_validate(raw)
    except ValidationError as exc:
        raise ScenarioError(f"{path}: {exc}") from exc


def load_scenarios(directory: Path = DATA_DIR) -> list[Scenario]:
    """Load every ``*.yaml``/``*.yml`` file under ``directory``, sorted by id."""
    files = sorted([*directory.rglob("*.yaml"), *directory.rglob("*.yml")])
    scenarios = [load_scenario_file(f, root=directory) for f in files]
    _check_unique(scenarios)
    return sorted(scenarios, key=lambda s: s.id)


def select_scenarios(selector: str, directory: Path = DATA_DIR) -> list[Scenario]:
    """Return all scenarios (``"all"``) or those whose ids are in a comma-separated list."""
    scenarios = load_scenarios(directory)
    if selector == "all":
        return scenarios
    by_id = {s.id: s for s in scenarios}
    wanted = [s.strip() for s in selector.split(",") if s.strip()]
    missing = [w for w in wanted if w not in by_id]
    if missing:
        raise ScenarioError(f"unknown scenario(s) {missing}; available: {sorted(by_id)}")
    return [by_id[w] for w in wanted]


def _check_unique(scenarios: Iterable[Scenario]) -> None:
    seen: set[str] = set()
    for s in scenarios:
        if s.id in seen:
            raise ScenarioError(f"duplicate scenario id {s.id!r}")
        seen.add(s.id)
