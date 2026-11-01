"""Mock MCP servers (built on the official ``mcp`` SDK) that make up the agent's sandbox.

Every server runs as a stdio subprocess, ``python -m arena.servers.<name>
--state-dir DIR``, so that proxy defenses can wrap it. Its state lives in that
directory, and the judge reads it there after the run.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any

from mcp import StdioServerParameters

from arena.servers._state import AGENT_IDENTITY, ServerState, StateStore

SERVER_NAMES: tuple[str, ...] = ("filesystem", "mail", "web", "issues", "sink", "shell")
"""Names of all mock servers. Each one is the module ``arena.servers.<name>``."""

_JSON_STATE_SERVERS: tuple[str, ...] = ("mail", "web", "issues", "sink", "shell")


def _store(name: str, state_dir: Path) -> StateStore[Any]:
    # Imported lazily so `python -m arena.servers.<name>` does not import its own
    # module twice (runpy warns about that).
    if name not in _JSON_STATE_SERVERS:
        raise ValueError(f"server {name!r} has no JSON state")
    store: StateStore[Any] = importlib.import_module(f"arena.servers.{name}").store(state_dir)
    return store


def stdio_params(name: str, state_dir: Path) -> StdioServerParameters:
    """Return the parameters that launch mock server ``name`` over stdio."""
    if name not in SERVER_NAMES:
        raise ValueError(f"unknown server {name!r}; expected one of {SERVER_NAMES}")
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", f"arena.servers.{name}", "--state-dir", str(Path(state_dir).resolve())],
    )


def load_state(name: str, state_dir: Path) -> ServerState:
    """Load the persisted state of file-backed server ``name`` (not ``filesystem``)."""
    state: ServerState = _store(name, state_dir).load()
    return state


def outbound_texts(state_dir: Path) -> dict[str, list[str]]:
    """Collect everything the agent sent out of the sandbox, keyed by server name."""
    return {name: load_state(name, state_dir).outbound_texts() for name in _JSON_STATE_SERVERS}


__all__ = [
    "AGENT_IDENTITY",
    "SERVER_NAMES",
    "ServerState",
    "StateStore",
    "load_state",
    "outbound_texts",
    "stdio_params",
]
