"""File-backed server state shared by the mock MCP servers.

Servers run as stdio subprocesses (so proxy defenses can wrap them), which means
their state must live on disk for the judge to inspect it after the run. Each
server keeps one pydantic model in ``<state_dir>/<name>.json``. Each tool call
reloads it and writes it back atomically.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

AGENT_IDENTITY = "arena-agent"
"""Name the agent acts under in servers that record an author (issues, chat)."""


class ServerState(BaseModel):
    """Base class for the persisted state of one mock server."""

    model_config = ConfigDict(extra="forbid")

    def outbound_texts(self) -> list[str]:
        """Return every string the agent sent across the sandbox boundary.

        The judge scans these for canaries. Subclasses override this. The default
        is "nothing leaves", which fits purely local servers.
        """
        return []


StateT = TypeVar("StateT", bound=ServerState)


class StateStore(Generic[StateT]):
    """Load and save a server's state model as JSON in a state directory."""

    def __init__(self, state_dir: Path, filename: str, model: type[StateT]) -> None:
        """Create a store for ``model`` at ``state_dir / filename``."""
        self.path = Path(state_dir) / filename
        self.model = model

    def load(self) -> StateT:
        """Return the current state, or a fresh default state if none was saved."""
        if not self.path.exists():
            return self.model()
        return self.model.model_validate_json(self.path.read_text(encoding="utf-8"))

    def save(self, state: StateT) -> None:
        """Atomically write ``state`` to disk."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=f".{self.path.name}.")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(state.model_dump_json(indent=2))
            os.replace(tmp, self.path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise

    @contextmanager
    def update(self) -> Iterator[StateT]:
        """Load the state, let the caller mutate it, then save it."""
        state = self.load()
        yield state
        self.save(state)
