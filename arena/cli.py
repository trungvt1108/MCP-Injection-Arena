"""Command-line interface for MCP Injection Arena."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Annotated

import anyio
import typer

from arena import __version__
from arena.config import MOCK_MODEL, RunConfig
from arena.results import RunRecord

app = typer.Typer(
    name="arena",
    help="MCP Injection Arena: benchmark prompt-injection defenses for MCP-based agents.",
    no_args_is_help=True,
    add_completion=False,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"arena {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            help="Show the version and exit.",
            callback=_version_callback,
            is_eager=True,
        ),
    ] = False,
) -> None:
    """Benchmark prompt-injection defenses for MCP-based AI agents in a local sandbox."""


@app.command("run")
def run_cmd(
    model: Annotated[
        str,
        typer.Option(help=f"LiteLLM model string (e.g. ollama/llama3.1), or '{MOCK_MODEL}'."),
    ],
    scenario: Annotated[
        str, typer.Option(help="Scenario id, comma-separated ids, or 'all'.")
    ] = "all",
    defense: Annotated[str, typer.Option(help="Defense name (see `arena list`).")] = "none",
    repeats: Annotated[int, typer.Option(min=1, help="Runs per scenario.")] = 3,
    max_steps: Annotated[int, typer.Option(min=1, help="Maximum model calls per run.")] = 20,
    seed: Annotated[int, typer.Option(help="Base random seed.")] = 0,
    confirm: Annotated[
        str, typer.Option(help="Simulated user's answer to confirmations: 'yes' or 'no'.")
    ] = "yes",
    attack: Annotated[
        bool,
        typer.Option(
            "--attack/--no-attack",
            help="With --no-attack, remove the injection to measure clean utility.",
        ),
    ] = True,
    results_dir: Annotated[Path, typer.Option(help="Where to write results.")] = Path("results"),
    scenarios_dir: Annotated[
        Path | None, typer.Option(help="Load scenarios from here instead of the built-in set.")
    ] = None,
) -> None:
    """Run scenarios against a defense and model, writing results/<timestamp>.json."""
    from arena.experiment import run_experiment  # lazy: keeps `arena --help` fast

    if confirm not in ("yes", "no"):
        raise typer.BadParameter("must be 'yes' or 'no'", param_hint="--confirm")
    extra = {"scenarios_dir": scenarios_dir} if scenarios_dir else {}
    config = RunConfig.model_validate(
        dict(
            model=model,
            defense=defense,
            scenario=scenario,
            repeats=repeats,
            max_steps=max_steps,
            seed=seed,
            confirm_policy="always_yes" if confirm == "yes" else "always_no",
            attack=attack,
            results_dir=results_dir,
            **extra,
        )
    )

    def progress(r: RunRecord) -> None:
        if r.error:
            typer.echo(f"{r.run_id:<60} ERROR  {r.error}")
            return
        if r.attack_mode == "clean":
            attack = "no injection   "
        else:
            attack = "ATTACK SUCCEEDED" if r.attack_success else "attack blocked "
        utility = "utility ok" if r.utility_success else "utility FAILED"
        typer.echo(f"{r.run_id:<60} {attack}  {utility}")

    try:
        path, results = anyio.run(lambda: run_experiment(config, on_record=progress))
    except ValueError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=2) from exc

    totals: dict[str, list[RunRecord]] = defaultdict(list)
    for r in results.runs:
        totals[r.scenario_id].append(r)
    typer.echo("")
    for sid, runs in totals.items():
        # Errored runs say nothing about the defense, so they are not counted.
        ok = [r for r in runs if r.error is None]
        util = sum(r.utility_success for r in ok)
        errors = f", {len(runs) - len(ok)} errored (excluded)" if len(ok) < len(runs) else ""
        if config.attack:
            asr = sum(r.attack_success for r in ok)
            typer.echo(f"{sid}: attack success {asr}/{len(ok)}, utility {util}/{len(ok)}{errors}")
        else:
            typer.echo(f"{sid}: clean utility {util}/{len(ok)}{errors}")
    typer.echo(f"\nResults written to {path}")


@app.command("list")
def list_cmd(
    scenarios_dir: Annotated[
        Path | None, typer.Option(help="Load scenarios from here instead of the built-in set.")
    ] = None,
) -> None:
    """List available scenarios and defenses."""
    from arena.defenses import DEFENSES
    from arena.scenarios.loader import DATA_DIR, load_scenarios

    typer.echo("Scenarios:")
    for s in load_scenarios(scenarios_dir or DATA_DIR):
        typer.echo(f"  {s.id:<40} [{s.category}] {s.title}")
    typer.echo("\nDefenses:")
    for name, make in sorted(DEFENSES.items()):
        typer.echo(f"  {name} (v{make().version})")


@app.command("report")
def report_cmd() -> None:
    """Turn result JSON files into markdown tables and leaderboard data."""
    typer.echo("`arena report` is not implemented yet.", err=True)
    raise typer.Exit(code=1)


if __name__ == "__main__":  # pragma: no cover
    app()
