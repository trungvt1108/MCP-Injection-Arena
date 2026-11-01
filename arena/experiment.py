"""Run scenarios x repeats for one defense and model, and write a results file."""

from __future__ import annotations

import hashlib
import random
import re
import tempfile
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path

from arena import __version__
from arena.agent.llm import LLM, LiteLLMClient
from arena.agent.mock_llm import ScriptedLLM
from arena.agent.runner import TranscriptWriter, run_agent
from arena.config import MOCK_MODEL, RunConfig
from arena.defenses import DefenseContext, ToolEvent, get_defense
from arena.judges import RunEvidence, judge_scenario
from arena.results import CheckRecord, LatencyRecord, ResultsFile, RunRecord, ToolCallRecord
from arena.scenarios.environment import Materialized, materialize
from arena.scenarios.loader import select_scenarios
from arena.scenarios.schema import Scenario
from arena.servers import stdio_params

LLMFactory = Callable[[Scenario, Materialized, int], LLM]
"""Builds the model for one run from (scenario, environment, seed)."""


def derive_seed(base: int, scenario_id: str, repeat: int) -> int:
    """Derive a stable 32-bit seed for one (scenario, repeat)."""
    digest = hashlib.sha256(f"{base}:{scenario_id}:{repeat}".encode()).digest()
    return int.from_bytes(digest[:4], "big")


def slug(text: str) -> str:
    """Make ``text`` safe to use in a file name."""
    return re.sub(r"[^A-Za-z0-9._-]+", "-", text).strip("-") or "x"


def default_llm_factory(config: RunConfig) -> LLMFactory:
    """Return the factory for ``config.model``: the scripted mock or LiteLLM."""

    def factory(scenario: Scenario, env: Materialized, seed: int) -> LLM:
        if config.model == MOCK_MODEL:
            if not scenario.mock_trajectory:
                raise ValueError(f"scenario {scenario.id!r} has no mock_trajectory")
            return ScriptedLLM.from_trajectory(scenario.mock_trajectory, env.substitutions)
        return LiteLLMClient(
            config.model, temperature=config.temperature, seed=seed, timeout=config.llm_timeout
        )

    return factory


async def run_one(
    scenario: Scenario,
    config: RunConfig,
    repeat: int,
    *,
    llm_factory: LLMFactory,
    transcript_path: Path,
    transcript_ref: str,
) -> RunRecord:
    """Run one scenario once and judge it."""
    seed = derive_seed(config.seed, scenario.id, repeat)
    defense = get_defense(config.defense)
    # Clean-utility runs remove the injected content by rendering it to nothing.
    payload_override = None if config.attack else ""
    with tempfile.TemporaryDirectory(prefix="arena-", ignore_cleanup_errors=True) as tmp:
        env = materialize(scenario, Path(tmp), random.Random(seed), payload=payload_override)
        servers = {
            name: defense.wrap_server(stdio_params(name, env.state_dir))
            for name in scenario.servers
        }
        ctx = DefenseContext(scenario_id=scenario.id, user_task=scenario.user_task)
        llm = llm_factory(scenario, env, seed)
        with TranscriptWriter(transcript_path) as log:
            log.write(
                "run",
                scenario=scenario.id,
                defense=defense.name,
                defense_version=defense.version,
                model=llm.name,
                repeat=repeat,
                seed=seed,
                canaries={name: c.value for name, c in env.canaries.items()},
            )
            try:
                run = await run_agent(
                    llm=llm,
                    servers=servers,
                    user_task=scenario.user_task,
                    defense=defense,
                    ctx=ctx,
                    max_steps=config.max_steps,
                    confirm_policy=config.confirm_policy,
                    transcript=log,
                )
            finally:
                await defense.close()
            attack, checks = judge_scenario(
                scenario, _evidence(env, run.final_answer, run.tool_events)
            )
            log.write("verdict", attack=attack.passed, attack_detail=attack.detail)

    return RunRecord(
        run_id=f"{scenario.id}/{defense.name}/{slug(config.model)}/{repeat}",
        scenario_id=scenario.id,
        scenario_category=scenario.category,
        injection_technique=scenario.injection.technique if scenario.injection else None,
        injection_template=scenario.injection.template if scenario.injection else None,
        attack_mode="attack" if config.attack else "clean",
        defense=defense.name,
        defense_version=defense.version,
        model=config.model,
        repeat=repeat,
        seed=seed,
        attack_success=attack.passed,
        attack_detail=attack.detail,
        utility_success=all(c.passed for c in checks),
        utility_checks=[
            CheckRecord(type=spec.type, passed=v.passed, detail=v.detail)
            for spec, v in zip(scenario.utility, checks, strict=True)
        ],
        confirmations=run.confirmations,
        steps=run.steps,
        stop_reason=run.stop_reason,
        final_answer=run.final_answer,
        tool_calls=[
            ToolCallRecord(
                id=e.call.id,
                server=e.call.server,
                name=e.call.name,
                arguments=e.call.arguments,
                decision=e.decision,
                reason=e.reason,
                executed=e.executed,
                is_error=bool(e.result and e.result.is_error),
            )
            for e in run.tool_events
        ],
        latency=LatencyRecord(**vars(run.latency)),
        usage=run.usage,
        transcript=transcript_ref,
        error=run.error,
    )


def _evidence(env: Materialized, final_answer: str, events: Sequence[ToolEvent]) -> RunEvidence:
    return RunEvidence(
        state_dir=env.state_dir,
        canaries=env.canaries,
        initial_files=env.initial_files,
        final_answer=final_answer,
        tool_events=list(events),
    )


async def run_experiment(
    config: RunConfig,
    *,
    llm_factory: LLMFactory | None = None,
    on_record: Callable[[RunRecord], None] | None = None,
    now: datetime | None = None,
) -> tuple[Path, ResultsFile]:
    """Run every selected scenario ``config.repeats`` times and write the results file.

    Returns:
        The path of the results JSON and its contents.
    """
    scenarios = select_scenarios(config.scenario, config.scenarios_dir)
    get_defense(config.defense)  # fail fast on an unknown name, before any run starts
    factory = llm_factory or default_llm_factory(config)
    created = now or datetime.now(UTC)
    stamp = created.strftime("%Y%m%dT%H%M%SZ")
    results_dir = config.results_dir
    results_dir.mkdir(parents=True, exist_ok=True)
    out_path = results_dir / f"{stamp}.json"
    n = 1
    while out_path.exists() or (results_dir / out_path.stem).exists():
        out_path = results_dir / f"{stamp}-{n}.json"
        n += 1
    transcripts_dir = results_dir / out_path.stem

    records: list[RunRecord] = []
    for scenario in scenarios:
        for repeat in range(config.repeats):
            name = f"{scenario.id}__{slug(config.defense)}__{slug(config.model)}__r{repeat}.jsonl"
            record = await run_one(
                scenario,
                config,
                repeat,
                llm_factory=factory,
                transcript_path=transcripts_dir / name,
                transcript_ref=f"{transcripts_dir.name}/{name}",
            )
            records.append(record)
            if on_record is not None:
                on_record(record)

    results = ResultsFile(
        arena_version=__version__,
        created_at=created.isoformat(),
        config=config.model_dump(mode="json", exclude={"results_dir", "scenarios_dir"}),
        runs=records,
    )
    out_path.write_text(results.model_dump_json(indent=2), encoding="utf-8")
    return out_path, results
