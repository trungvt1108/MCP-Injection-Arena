"""The third-party defense adapters are researched but pending integration.

These tests pin that contract: each adapter is discoverable with its metadata,
none is registered as a usable defense yet, and each ``build()`` raises with
concrete guidance instead of guessing an API.
"""

import pytest

from arena.defenses import DEFENSES
from arena.defenses.external import ADAPTERS, fides, mcpkernel, sluice


def test_adapters_are_enumerated() -> None:
    assert set(ADAPTERS) == {"fides", "mcpkernel", "sluice"}


def test_adapters_are_not_registered_as_usable_defenses() -> None:
    assert set(DEFENSES).isdisjoint(ADAPTERS)


def test_verified_adapters_pin_a_version() -> None:
    assert ADAPTERS["fides"].pinned_version  # agent-framework-core floor
    assert ADAPTERS["mcpkernel"].pinned_version == "0.3.0"
    assert ADAPTERS["mcpkernel"].license == "Apache-2.0"


def test_unresolved_sluice_is_marked_unverified() -> None:
    assert ADAPTERS["sluice"].package == ""
    assert ADAPTERS["sluice"].pinned_version == ""
    assert ADAPTERS["sluice"].status == "unverified-identity"


@pytest.mark.parametrize(
    ("module", "needle"),
    [
        (fides, "runner backend"),
        (mcpkernel, "HTTP"),
        (sluice, "does not identify a single project"),
    ],
)
def test_build_raises_with_guidance(module: object, needle: str) -> None:
    with pytest.raises(NotImplementedError) as exc:
        module.build()  # type: ignore[attr-defined]
    assert needle in str(exc.value)
