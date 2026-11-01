"""Schema of the results files written to ``results/<timestamp>.json``."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

SCHEMA_VERSION = 1


class ToolCallRecord(BaseModel):
    """One tool call and what the defense decided."""

    id: str
    server: str
    name: str
    arguments: dict[str, Any]
    decision: str
    reason: str = ""
    executed: bool
    is_error: bool = False


class CheckRecord(BaseModel):
    """The outcome of one judge check."""

    type: str
    passed: bool
    detail: str


class LatencyRecord(BaseModel):
    """Seconds spent in each part of a run."""

    total: float
    llm: float
    tools: float
    defense: float


class RunRecord(BaseModel):
    """One (scenario, defense, model, repeat) run."""

    run_id: str
    scenario_id: str
    scenario_category: str
    injection_technique: str | None
    injection_template: str | None = None
    attack_mode: str = "attack"
    """``"attack"`` with the injection present, or ``"clean"`` for a --no-attack run."""
    defense: str
    defense_version: str
    model: str
    repeat: int
    seed: int
    attack_success: bool
    attack_detail: str
    utility_success: bool
    utility_checks: list[CheckRecord]
    confirmations: int
    steps: int
    stop_reason: str
    final_answer: str
    tool_calls: list[ToolCallRecord]
    latency: LatencyRecord
    usage: dict[str, int] = Field(default_factory=dict)
    transcript: str
    """Path of the JSONL transcript, relative to the results directory."""
    error: str | None = None


class ResultsFile(BaseModel):
    """A whole ``arena run``: its configuration and every run record."""

    schema_version: int = SCHEMA_VERSION
    arena_version: str
    created_at: str
    config: dict[str, Any]
    runs: list[RunRecord]
