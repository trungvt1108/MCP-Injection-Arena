"""Run configuration."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from arena.agent.runner import ConfirmPolicy
from arena.scenarios.loader import DATA_DIR

MOCK_MODEL = "mock"
"""Model name that plays back each scenario's ``mock_trajectory`` offline."""


class RunConfig(BaseModel):
    """Everything that determines a benchmark run. Saved in every results file."""

    model_config = ConfigDict(extra="forbid")

    model: str
    """LiteLLM model string (e.g. ``ollama/llama3.1``) or ``mock``."""
    defense: str = "none"
    scenario: str = "all"
    """``all`` or a comma-separated list of scenario ids."""
    repeats: int = Field(default=3, ge=1)
    max_steps: int = Field(default=20, ge=1)
    temperature: float = 0.0
    seed: int = 0
    """Base seed. Each (scenario, repeat) derives its own seed from it."""
    confirm_policy: ConfirmPolicy = "always_yes"
    llm_timeout: float = 120.0
    results_dir: Path = Path("results")
    scenarios_dir: Path = DATA_DIR
