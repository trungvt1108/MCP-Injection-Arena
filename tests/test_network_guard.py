import socket

import pytest

from tests.conftest import NetworkAccessError


def test_outbound_connection_is_blocked() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s, pytest.raises(NetworkAccessError):
        s.connect(("192.0.2.1", 80))  # TEST-NET-1, never routable


def test_loopback_is_allowed() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
            client.connect(server.getsockname())
