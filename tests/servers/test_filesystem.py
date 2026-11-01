import os
from pathlib import Path

import pytest

from arena.servers import filesystem
from tests.servers.helpers import call, tool_names

pytestmark = pytest.mark.anyio

FILES = {
    "README.md": "# Demo project\n",
    ".env": "API_KEY=sk-arena-secret\n",
    "src/app.py": "print('hi')\n",
}


@pytest.fixture
def state_dir(tmp_path: Path) -> Path:
    filesystem.seed(tmp_path, FILES)
    return tmp_path


async def test_tools(state_dir: Path) -> None:
    server = filesystem.create_server(state_dir)
    assert await tool_names(server) == {"list_directory", "read_file", "write_file", "delete_file"}


async def test_list_directory_shows_hidden_files_and_dirs(state_dir: Path) -> None:
    result = await call(filesystem.create_server(state_dir), "list_directory")
    assert result.text.splitlines() == [".env", "README.md", "src/"]
    sub = await call(filesystem.create_server(state_dir), "list_directory", path="src")
    assert sub.text == "app.py"


async def test_read_file(state_dir: Path) -> None:
    result = await call(filesystem.create_server(state_dir), "read_file", path=".env")
    assert result.text == FILES[".env"]
    assert not result.is_error


async def test_leading_slash_means_workspace_root(state_dir: Path) -> None:
    result = await call(filesystem.create_server(state_dir), "read_file", path="/src/app.py")
    assert result.text == FILES["src/app.py"]


async def test_write_and_snapshot(state_dir: Path) -> None:
    server = filesystem.create_server(state_dir)
    result = await call(server, "write_file", path="notes/todo.txt", content="buy milk")
    assert not result.is_error
    snap = filesystem.snapshot(state_dir)
    assert snap["notes/todo.txt"] == b"buy milk"
    assert set(snap) == {*FILES, "notes/todo.txt"}


async def test_delete_file_is_visible_in_snapshot(state_dir: Path) -> None:
    await call(filesystem.create_server(state_dir), "delete_file", path="README.md")
    assert "README.md" not in filesystem.snapshot(state_dir)


async def test_missing_file_is_a_tool_error(state_dir: Path) -> None:
    result = await call(filesystem.create_server(state_dir), "read_file", path="nope.txt")
    assert result.is_error
    assert "not found" in result.text.lower()


async def test_cannot_delete_directory(state_dir: Path) -> None:
    result = await call(filesystem.create_server(state_dir), "delete_file", path="src")
    assert result.is_error
    assert (state_dir / "fs" / "src").is_dir()


@pytest.mark.parametrize(
    "path",
    ["../outside.txt", "src/../../outside.txt", "..\\outside.txt", str(Path.home() / "x.txt")],
)
async def test_path_traversal_is_denied(state_dir: Path, path: str) -> None:
    (state_dir / "outside.txt").write_text("host file")
    server = filesystem.create_server(state_dir)
    for tool, args in [
        ("read_file", {"path": path}),
        ("write_file", {"path": path, "content": "pwned"}),
        ("delete_file", {"path": path}),
    ]:
        result = await call(server, tool, **args)
        assert result.is_error
        assert "denied" in result.text.lower() or "not found" in result.text.lower()
    assert (state_dir / "outside.txt").read_text() == "host file"


async def test_symlink_escape_is_denied(state_dir: Path) -> None:
    secret = state_dir / "host-secret.txt"
    secret.write_text("host secret")
    link = state_dir / "fs" / "link.txt"
    try:
        os.symlink(secret, link)
    except OSError:
        pytest.skip("creating symlinks is not permitted on this machine")
    result = await call(filesystem.create_server(state_dir), "read_file", path="link.txt")
    assert result.is_error
    assert "host secret" not in result.text


def test_seed_rejects_escaping_paths(tmp_path: Path) -> None:
    with pytest.raises(Exception, match="outside"):
        filesystem.seed(tmp_path, {"../evil": "x"})


def test_snapshot_of_missing_sandbox_is_empty(tmp_path: Path) -> None:
    assert filesystem.snapshot(tmp_path) == {}
