"""Mock web MCP server that serves local fixture pages.

There is no network access. ``fetch_url`` looks the URL up in the fixture pages,
some of which carry injections. Every URL fetched and every search query is
logged, because a URL is an exfiltration channel too
(``https://attacker.example/?q=<secret>``).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from mcp.server.mcpserver import MCPServer
from pydantic import BaseModel, Field

from arena.servers._main import run_stdio
from arena.servers._state import ServerState, StateStore

SERVER_NAME = "web"
STATE_FILE = "web.json"


class Page(BaseModel):
    """A fixture web page."""

    url: str
    title: str = ""
    content: str


class WebRequest(BaseModel):
    """One request the agent made."""

    kind: str
    """``"fetch"`` or ``"search"``."""
    value: str
    """The URL fetched or the query searched."""
    found: bool


class WebState(ServerState):
    """Fixture pages and the log of requests."""

    pages: list[Page] = Field(default_factory=list)
    requests: list[WebRequest] = Field(default_factory=list)

    def outbound_texts(self) -> list[str]:
        """Every URL requested and every search query sent."""
        return [r.value for r in self.requests]


def store(state_dir: Path) -> StateStore[WebState]:
    """Return the state store for the web server in ``state_dir``."""
    return StateStore(state_dir, STATE_FILE, WebState)


def page_key(url: str) -> str:
    """Normalize a URL for page lookup: host case-folded, query and fragment ignored."""
    parts = urlsplit(url.strip())
    if not parts.netloc and not parts.scheme:  # "example.com/docs"
        parts = urlsplit(f"https://{url.strip()}")
    path = parts.path.rstrip("/") or "/"
    return f"{parts.netloc.casefold()}{path}"


def create_server(state_dir: Path) -> MCPServer[Any]:
    """Build the web server backed by ``state_dir``."""
    st = store(state_dir)
    server: MCPServer[Any] = MCPServer(
        name=SERVER_NAME,
        instructions="Fetch web pages and search the web.",
    )

    @server.tool()
    def fetch_url(url: str) -> str:
        """Fetch a web page and return its text content."""
        with st.update() as state:
            key = page_key(url)
            page = next((p for p in state.pages if page_key(p.url) == key), None)
            state.requests.append(WebRequest(kind="fetch", value=url, found=page is not None))
        if page is None:
            return f"404 Not Found: {url}"
        title = f"# {page.title}\n\n" if page.title else ""
        return f"{title}{page.content}"

    @server.tool()
    def search_web(query: str) -> str:
        """Search the web. Returns matching page titles and URLs."""
        words = [w for w in query.casefold().split() if w]
        with st.update() as state:
            hits = [
                p
                for p in state.pages
                if words and all(w in f"{p.title}\n{p.content}".casefold() for w in words)
            ]
            state.requests.append(WebRequest(kind="search", value=query, found=bool(hits)))
        if not hits:
            return "No results."
        return "\n".join(f"{p.title or p.url} - {p.url}" for p in hits)

    return server


def main() -> None:
    """Run the web server over stdio."""
    run_stdio(create_server)


if __name__ == "__main__":
    main()
