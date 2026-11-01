import os
import re
import uuid
from pathlib import Path

import pytest
from mcp.server.mcpserver.exceptions import ToolError

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


async def test_leading_slash_is_rejected_not_reinterpreted(state_dir: Path) -> None:
    # "/src/app.py" used to be silently mapped to "<root>/src/app.py". Absolute
    # paths are now refused outright, the same on every OS.
    result = await call(filesystem.create_server(state_dir), "read_file", path="/src/app.py")
    assert result.is_error
    assert "absolute paths are not allowed" in result.text


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


# --- cross-platform path handling ------------------------------------------------
# Every case below runs on every OS: Windows-style paths are exercised on Linux and
# POSIX paths on Windows. Path handling must not depend on the host.

REJECTED = {
    # POSIX absolute
    "/etc/passwd": "absolute paths",
    "/tmp/x.txt": "absolute paths",
    "/": "absolute paths",
    # Windows absolute / rooted (raw strings: each backslash is one character)
    r"C:\Windows\win.ini": "drive paths",
    "C:/Windows/win.ini": "drive paths",
    "c:x.txt": "drive paths",
    r"\x.txt": "absolute paths",
    # UNC and device paths
    r"\\server\share\x.txt": "UNC paths",
    "//server/share/x.txt": "UNC paths",
    r"\\?\C:\x.txt": "UNC paths",
    # home expansion
    "~": "home-directory",
    "~/x.txt": "home-directory",
    "~root/x.txt": "home-directory",
    r"~\x.txt": "home-directory",
    # traversal, either separator
    "../x.txt": "outside the workspace",
    r"..\x.txt": "outside the workspace",
    r"src\..\..\x.txt": "outside the workspace",
    "src/../../x.txt": "outside the workspace",
    "a/b/../../../x.txt": "outside the workspace",
    # names some OS would treat specially
    "notes.txt:hidden": "invalid character",
    "a?b.txt": "invalid character",
    "a\x00b.txt": "invalid character",
    "NUL": "reserved device name",
    "src/con.txt": "reserved device name",
    "COM1": "reserved device name",
    "secret.txt.": "dot or space",
    "secret.txt ": "dot or space",
    "src/app.py ": "dot or space",
    " /etc/passwd": "dot or space",
    r" C:\x.txt": "invalid character",
}


def all_paths_under(base: Path) -> set[str]:
    return {p.relative_to(base).as_posix() for p in base.rglob("*")}


@pytest.mark.parametrize("raw", REJECTED, ids=[repr(k) for k in REJECTED])
def test_resolve_path_rejects(tmp_path: Path, raw: str) -> None:
    root = tmp_path / "fs"
    root.mkdir()
    with pytest.raises(ToolError, match=re.escape(REJECTED[raw])):
        filesystem.resolve_path(root, raw)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (".", ""),
        ("", ""),
        ("src/app.py", "src/app.py"),
        (r"src\app.py", "src/app.py"),
        ("./src//app.py", "src/app.py"),
        ("src/../README.md", "README.md"),
        (r"src\..\README.md", "README.md"),
        ("backup~/a.txt", "backup~/a.txt"),
        ("console.txt", "console.txt"),
    ],
)
def test_resolve_path_accepts(state_dir: Path, raw: str, expected: str) -> None:
    root = filesystem.sandbox_root(state_dir)
    resolved = filesystem.resolve_path(root, raw)
    assert resolved == (root.resolve() / expected).resolve()


@pytest.mark.parametrize("raw", REJECTED, ids=[repr(k) for k in REJECTED])
async def test_rejected_paths_touch_nothing(state_dir: Path, raw: str) -> None:
    before = all_paths_under(state_dir)
    server = filesystem.create_server(state_dir)
    for tool, args in [
        ("write_file", {"path": raw, "content": "pwned"}),
        ("write_file", {"path": f"{raw}/nested/x.txt", "content": "pwned"}),
        ("delete_file", {"path": raw}),
        ("read_file", {"path": raw}),
        ("list_directory", {"path": raw}),
    ]:
        result = await call(server, tool, **args)
        assert result.is_error, (tool, raw, result.text)
        assert "Access denied" in result.text, result.text
    # Fail closed: nothing created, not even inside the sandbox.
    assert all_paths_under(state_dir) == before


def absolute_spellings(target: Path) -> list[str]:
    """The same absolute location written natively, with '/' and with backslashes."""
    native = str(target)
    return sorted({native, native.replace("\\", "/"), native.replace("/", "\\")})


async def test_absolute_paths_do_not_create_the_real_file(state_dir: Path, tmp_path: Path) -> None:
    victim_dir = tmp_path / "victim"
    victim_dir.mkdir()
    victim = victim_dir / "x.txt"
    before = all_paths_under(tmp_path)
    server = filesystem.create_server(state_dir)
    for raw in absolute_spellings(victim):
        result = await call(server, "write_file", path=raw, content="pwned")
        assert result.is_error, raw
    assert not victim.exists()
    assert all_paths_under(tmp_path) == before


async def test_home_path_does_not_create_the_real_file(state_dir: Path) -> None:
    name = f"arena-test-{uuid.uuid4().hex}.txt"
    real = Path.home() / name
    server = filesystem.create_server(state_dir)
    try:
        for raw in (f"~/{name}", rf"~\{name}", *absolute_spellings(real)):
            result = await call(server, "write_file", path=raw, content="pwned")
            assert result.is_error, raw
        assert not real.exists()
        assert not any(name in p for p in all_paths_under(state_dir))
    finally:
        real.unlink(missing_ok=True)


async def test_traversal_does_not_create_sibling_file(state_dir: Path) -> None:
    server = filesystem.create_server(state_dir)
    for raw in ("../escaped.txt", r"..\escaped.txt", r"src\..\..\escaped.txt"):
        assert (await call(server, "write_file", path=raw, content="pwned")).is_error
    assert not (state_dir / "escaped.txt").exists()
    assert not any("escaped" in p for p in all_paths_under(state_dir))


async def test_backslash_is_a_separator_on_every_os(state_dir: Path) -> None:
    server = filesystem.create_server(state_dir)
    assert not (await call(server, "write_file", path=r"notes\todo.txt", content="x")).is_error
    assert filesystem.snapshot(state_dir)["notes/todo.txt"] == b"x"
    assert (await call(server, "read_file", path=r"src\app.py")).text == FILES["src/app.py"]
    assert (await call(server, "list_directory", path="src\\")).text == "app.py"


async def test_directory_symlink_escape_is_denied(state_dir: Path, tmp_path: Path) -> None:
    outside = tmp_path / "outside-dir"
    outside.mkdir()
    try:
        os.symlink(outside, filesystem.sandbox_root(state_dir) / "linked", target_is_directory=True)
    except OSError:
        pytest.skip("creating symlinks is not permitted on this machine")
    server = filesystem.create_server(state_dir)
    result = await call(server, "write_file", path="linked/x.txt", content="pwned")
    assert result.is_error
    assert "outside the workspace" in result.text
    assert list(outside.iterdir()) == []
