"""Adapters for third-party prompt-injection defenses.

Each third-party defense lives in its own module (``fides``, ``mcpkernel``,
``sluice``). All three are researched but **pending integration**: their
``build()`` raises ``NotImplementedError`` with the exact steps still to verify,
so nothing here is registered in :data:`arena.defenses.DEFENSES` yet. See
``docs/adding-a-defense.md`` for the status of each and why.

``ADAPTERS`` lets tooling and docs enumerate them without importing a package
that may not be installed.
"""

from __future__ import annotations

from dataclasses import dataclass

from arena.defenses.external import fides, mcpkernel, sluice


@dataclass(frozen=True)
class AdapterInfo:
    """Static metadata about a (pending) third-party defense adapter."""

    name: str
    package: str
    pinned_version: str
    license: str
    status: str


ADAPTERS: dict[str, AdapterInfo] = {
    mod.NAME: AdapterInfo(
        name=mod.NAME,
        package=mod.PACKAGE,
        pinned_version=mod.PINNED_VERSION,
        license=getattr(mod, "LICENSE", ""),
        status=mod.STATUS,
    )
    for mod in (fides, mcpkernel, sluice)
}
"""Name -> metadata for every third-party adapter, verified or not."""

__all__ = ["ADAPTERS", "AdapterInfo", "fides", "mcpkernel", "sluice"]
