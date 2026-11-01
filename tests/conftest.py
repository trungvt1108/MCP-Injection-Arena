"""Shared pytest fixtures.

Tests must never make network calls (see CLAUDE.md). The autouse fixture below
blocks every outbound socket connection that is not to a loopback address, so a
test that accidentally reaches the internet fails loudly instead of silently
passing.
"""

from __future__ import annotations

import ipaddress
import socket
from collections.abc import Iterator
from typing import Any

import pytest


class NetworkAccessError(RuntimeError):
    """Raised when a test tries to open a non-loopback network connection."""


def _is_loopback(address: Any) -> bool:
    if isinstance(address, str):  # AF_UNIX path
        return True
    if not isinstance(address, tuple) or not address:
        return False
    host = address[0]
    if host in ("localhost", ""):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


@pytest.fixture(autouse=True)
def _block_network(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex

    def guarded_connect(self: socket.socket, address: Any) -> None:
        if not _is_loopback(address):
            raise NetworkAccessError(f"tests must not use the network (tried {address!r})")
        real_connect(self, address)

    def guarded_connect_ex(self: socket.socket, address: Any) -> int:
        if not _is_loopback(address):
            raise NetworkAccessError(f"tests must not use the network (tried {address!r})")
        return real_connect_ex(self, address)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", guarded_connect_ex)
    yield


@pytest.fixture
def anyio_backend() -> str:
    """Run ``@pytest.mark.anyio`` tests on asyncio only."""
    return "asyncio"
