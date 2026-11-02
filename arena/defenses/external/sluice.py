"""Adapter (pending) for "Sluice" - identity UNVERIFIED.

Status: NOT YET INTEGRATED, and blocked earlier than the others: "Sluice" does not
name a single project. Per the project rule (do not invent third-party APIs),
``build()`` raises until the intended package is pinned down. ``PINNED_VERSION`` is
deliberately empty.

What the search found (2026-11-02): several unrelated MCP projects share the name.
Each would need its own verification:

* ``sluice-mcp`` (github.com/premm25/sluice, PyPI 0.1.0) - "information-flow
  control proxy for MCP agents: blocks private-data exfiltration (even base64/hex),
  quarantines poisoned tools, detects rug pulls; pure Python, zero deps". This is
  the closest match to the arena's own ``reference_taint`` idea and the most likely
  intended target.
* ``sluice-taint`` (github.com/krishyaid-coder/sluice) - "local MCP gate that
  remembers sensitive values across tool calls and blocks them from being sent
  again"; runs as ``sluice stdio``.
* ``mcp-sluice`` (PyPI) - unrelated; materializes tool results into DuckDB; needs
  Python 3.14+.

TODO (resolve before writing any adapter; do not guess an API):
  1. Decide which "Sluice" is meant (most likely ``sluice-mcp`` / premm25). Record
     the PyPI name, a pinned version, and the license (read the repo's LICENSE).
  2. Read its source to find how it runs: does it expose a stdio-to-stdio MCP proxy
     (a command the arena can wrap via ``wrap_server`` -> ``StdioServerParameters``),
     or only a CLI/HTTP gateway? Confirm the exact invocation and config format.
  3. Only then implement: if it is a stdio proxy, ``wrap_server`` should return
     params that launch the arena's server command *behind* Sluice; map its
     block/confirm outcomes into the run's accounting.
"""

from __future__ import annotations

from typing import NoReturn

NAME = "sluice"
PACKAGE = ""  # UNRESOLVED: candidates sluice-mcp, sluice-taint, mcp-sluice
PINNED_VERSION = ""  # do not pin until the project is identified
LICENSE = ""  # verify from the chosen repo
STATUS = "unverified-identity"


def build() -> NoReturn:
    """Raise: which "Sluice"? Package identity is unresolved. See module docstring."""
    raise NotImplementedError(
        "'Sluice' does not identify a single project (candidates: sluice-mcp / "
        "premm25, sluice-taint / krishyaid-coder, mcp-sluice). Pick the intended "
        "package, pin its version and license, and verify whether it is a "
        "stdio MCP proxy before writing an adapter (see the TODO in "
        "arena/defenses/external/sluice.py)."
    )
