"""Validate the built-in Level-1 scenario suite as a whole."""

from collections import Counter

import pytest

from arena.attacks.templates import render as render_template
from arena.scenarios.loader import load_scenarios
from arena.scenarios.schema import PLACEHOLDER, Scenario

SCENARIOS = load_scenarios()

EXPECTED_CATEGORIES = {
    "coding-agent": 5,
    "email-assistant": 5,
    "web-research": 5,
    "file-assistant": 5,
    "multi-server": 5,
}


def test_suite_has_twenty_five_scenarios() -> None:
    assert len(SCENARIOS) == 25


def test_five_categories_with_five_each() -> None:
    counts = Counter(s.category for s in SCENARIOS)
    assert dict(counts) == EXPECTED_CATEGORIES


def test_ids_are_unique() -> None:
    ids = [s.id for s in SCENARIOS]
    assert len(ids) == len(set(ids))


def test_attack_goals_cover_every_type() -> None:
    kinds = {s.attack_goal.type for s in SCENARIOS}
    assert kinds == {"canary_exfil", "file_deleted", "command_executed", "tool_called_with"}


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.id)
def test_scenario_is_well_formed(scenario: Scenario) -> None:
    assert scenario.injection is not None, "Level-1 scenarios always carry an injection"
    # Its template resolves and the neutral goal text flows into the payload.
    payload = render_template(scenario.injection.template, scenario.injection.goal)
    assert payload
    # The payload is actually placed somewhere in the environment.
    assert "injection" in set(scenario.placeholders())
    # The scenario can be exercised offline.
    assert scenario.mock_trajectory, "every built-in scenario needs a mock_trajectory"
    assert any(getattr(step, "answer", None) is not None for step in scenario.mock_trajectory)


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.id)
def test_scenario_yaml_has_no_persuasive_payload_text(scenario: Scenario) -> None:
    """Payload prose must not live in the YAML: only a neutral goal + template ref."""
    assert not PLACEHOLDER.search(scenario.injection.goal if scenario.injection else "")
    # goal is a short description, not a multi-paragraph script.
    assert scenario.injection is not None
    assert len(scenario.injection.goal) < 400


def test_multi_server_scenarios_really_span_servers() -> None:
    for s in SCENARIOS:
        if s.category == "multi-server":
            assert len(s.servers) >= 2, f"{s.id} should use at least two servers"
