from typer.testing import CliRunner

from arena import __version__
from arena.cli import app

runner = CliRunner()


def test_help_lists_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in ("run", "list", "report"):
        assert command in result.output


def test_no_args_shows_help() -> None:
    result = runner.invoke(app, [])
    assert "Usage" in result.output


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_unimplemented_command_fails_cleanly() -> None:
    result = runner.invoke(app, ["report"])
    assert result.exit_code == 1
