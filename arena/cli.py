"""Command-line interface for MCP Injection Arena.

Only the command surface exists so far; ``run``, ``list`` and ``report`` are
implemented in later phases.
"""

from typing import Annotated

import typer

from arena import __version__

app = typer.Typer(
    name="arena",
    help="MCP Injection Arena: benchmark prompt-injection defenses for MCP-based agents.",
    no_args_is_help=True,
    add_completion=False,
)


def _not_implemented(command: str) -> None:
    typer.echo(f"`arena {command}` is not implemented yet.", err=True)
    raise typer.Exit(code=1)


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
def run_cmd() -> None:
    """Run scenarios against a defense and model, writing results to results/."""
    _not_implemented("run")


@app.command("list")
def list_cmd() -> None:
    """List available scenarios, attacks and defenses."""
    _not_implemented("list")


@app.command("report")
def report_cmd() -> None:
    """Turn result JSON files into markdown tables and leaderboard data."""
    _not_implemented("report")


if __name__ == "__main__":  # pragma: no cover
    app()
