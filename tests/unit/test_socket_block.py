from __future__ import annotations

import socket

import pytest
from pytest_socket import SocketBlockedError


def test_network_is_blocked_by_default() -> None:
    with pytest.raises(SocketBlockedError):
        socket.create_connection(("example.com", 80), timeout=0.1)
