"""Mock GitHub-like issue tracker MCP server (issues, pull requests, comments).

Issues and pull requests share one number space, as on GitHub. Anything the agent
writes (new issues, comments) is treated as public and therefore outbound.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel, Field

from arena.servers._main import run_stdio
from arena.servers._state import AGENT_IDENTITY, ServerState, StateStore

SERVER_NAME = "issues"
STATE_FILE = "issues.json"


class Comment(BaseModel):
    """A comment on an issue or pull request."""

    author: str
    body: str


class Issue(BaseModel):
    """An issue or a pull request."""

    number: int
    kind: Literal["issue", "pull_request"] = "issue"
    title: str
    body: str = ""
    author: str = "octo-user"
    state: Literal["open", "closed"] = "open"
    labels: list[str] = Field(default_factory=list)
    comments: list[Comment] = Field(default_factory=list)


class IssuesState(ServerState):
    """The repository's issues and pull requests."""

    repo: str = "acme/webapp"
    issues: list[Issue] = Field(default_factory=list)

    def outbound_texts(self) -> list[str]:
        """Titles, bodies and comments written by the agent."""
        texts: list[str] = []
        for issue in self.issues:
            if issue.author == AGENT_IDENTITY:
                texts.append(f"{issue.title}\n{issue.body}")
            texts.extend(c.body for c in issue.comments if c.author == AGENT_IDENTITY)
        return texts

    def get(self, number: int) -> Issue:
        """Return issue or pull request ``number``."""
        for issue in self.issues:
            if issue.number == number:
                return issue
        raise ToolError(f"No issue or pull request #{number} in {self.repo}")


def store(state_dir: Path) -> StateStore[IssuesState]:
    """Return the state store for the issues server in ``state_dir``."""
    return StateStore(state_dir, STATE_FILE, IssuesState)


def _summary(issue: Issue) -> str:
    labels = f" [{', '.join(issue.labels)}]" if issue.labels else ""
    return f"#{issue.number} ({issue.state}) {issue.title}{labels} - by {issue.author}"


def _render(issue: Issue) -> str:
    kind = "Pull request" if issue.kind == "pull_request" else "Issue"
    out = f"{kind} #{issue.number}: {issue.title}\nAuthor: {issue.author}\nState: {issue.state}\n"
    if issue.labels:
        out += f"Labels: {', '.join(issue.labels)}\n"
    out += f"\n{issue.body}\n"
    for i, comment in enumerate(issue.comments, start=1):
        out += f"\n--- Comment {i} by {comment.author} ---\n{comment.body}\n"
    return out


def create_server(state_dir: Path) -> MCPServer[Any]:
    """Build the issues server backed by ``state_dir``."""
    st = store(state_dir)
    server: MCPServer[Any] = MCPServer(
        name=SERVER_NAME,
        instructions="Work with the issues and pull requests of the user's repository.",
    )

    def _list(kind: str, state_filter: str) -> str:
        state = st.load()
        hits = [
            i
            for i in state.issues
            if i.kind == kind and (state_filter == "all" or i.state == state_filter)
        ]
        return "\n".join(_summary(i) for i in hits) if hits else "None found."

    @server.tool()
    def list_issues(state: Literal["open", "closed", "all"] = "open") -> str:
        """List issues in the repository."""
        return _list("issue", state)

    @server.tool()
    def list_pull_requests(state: Literal["open", "closed", "all"] = "open") -> str:
        """List pull requests in the repository."""
        return _list("pull_request", state)

    @server.tool()
    def get_issue(number: int) -> str:
        """Read an issue or pull request, including all comments."""
        return _render(st.load().get(number))

    @server.tool()
    def create_issue(title: str, body: str = "") -> str:
        """Open a new issue."""
        with st.update() as state:
            number = max((i.number for i in state.issues), default=0) + 1
            state.issues.append(Issue(number=number, title=title, body=body, author=AGENT_IDENTITY))
        return f"Created issue #{number}."

    @server.tool()
    def add_comment(number: int, body: str) -> str:
        """Comment on an issue or pull request."""
        with st.update() as state:
            state.get(number).comments.append(Comment(author=AGENT_IDENTITY, body=body))
        return f"Comment added to #{number}."

    @server.tool()
    def close_issue(number: int) -> str:
        """Close an issue or pull request."""
        with st.update() as state:
            state.get(number).state = "closed"
        return f"Closed #{number}."

    return server


def main() -> None:
    """Run the issues server over stdio."""
    run_stdio(create_server)


if __name__ == "__main__":
    main()
