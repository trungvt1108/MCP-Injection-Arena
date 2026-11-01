"""Shared command-line entry point for running a mock server over stdio."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer


def run_stdio(
    create_server: Callable[[Path], MCPServer[Any]],
    argv: Sequence[str] | None = None,
) -> None:
    """Parse ``--state-dir`` and serve ``create_server(state_dir)`` over stdio."""
    parser = argparse.ArgumentParser(description="Run an MCP Injection Arena mock server.")
    parser.add_argument("--state-dir", type=Path, required=True, help="Directory holding state.")
    args = parser.parse_args(argv)
    create_server(args.state_dir).run("stdio")
