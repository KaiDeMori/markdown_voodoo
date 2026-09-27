"""The guard every other test relies on: no socket operation gets through."""
from __future__ import annotations

import socket

import pytest
import yt_dlp

from conftest import Network_blocked


def exception_chain(error: BaseException):
    """The error, its causes, and the handler errors yt-dlp collects without chaining."""
    seen, pending = [], [error]
    while pending:
        current = pending.pop()
        if current is None or current in seen:
            continue
        seen.append(current)
        pending += [current.__cause__, current.__context__, getattr(current, "cause", None),
                    *getattr(current, "unexpected_errors", [])]
    return seen


def test_socket_connections_are_refused():
    with pytest.raises(Network_blocked):
        socket.create_connection(("example.com", 443))


def test_name_resolution_is_refused():
    with pytest.raises(Network_blocked):
        socket.getaddrinfo("www.youtube.com", 443)


def test_yt_dlp_requests_are_refused():
    with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
        with pytest.raises(Exception) as caught:
            ydl.urlopen("https://example.com")
    assert any(isinstance(e, Network_blocked) for e in exception_chain(caught.value))
