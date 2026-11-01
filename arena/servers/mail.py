"""Mock email MCP server with an in-memory (file-backed) inbox and outbox.

Nothing is ever delivered. Sent mail is appended to ``outbox``, which the judge
reads for ``message_sent_to`` utility checks and canary exfiltration.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel, Field

from arena.servers._main import run_stdio
from arena.servers._state import AGENT_IDENTITY, ServerState, StateStore

SERVER_NAME = "mail"
STATE_FILE = "mail.json"


class Email(BaseModel):
    """One email message."""

    id: str
    sender: str
    to: list[str]
    subject: str
    body: str
    date: str = ""


class MailState(ServerState):
    """Inbox fixtures plus everything the agent sent."""

    owner: str = "user@example.com"
    inbox: list[Email] = Field(default_factory=list)
    outbox: list[Email] = Field(default_factory=list)

    def outbound_texts(self) -> list[str]:
        """Recipients, subjects and bodies of all sent mail."""
        return [f"{', '.join(m.to)}\n{m.subject}\n{m.body}" for m in self.outbox]


def store(state_dir: Path) -> StateStore[MailState]:
    """Return the state store for the mail server in ``state_dir``."""
    return StateStore(state_dir, STATE_FILE, MailState)


def _summary(mail: Email) -> str:
    date = f" {mail.date}" if mail.date else ""
    return f"[{mail.id}]{date} from {mail.sender}: {mail.subject}"


def _render(mail: Email) -> str:
    header = f"ID: {mail.id}\nFrom: {mail.sender}\nTo: {', '.join(mail.to)}\n"
    if mail.date:
        header += f"Date: {mail.date}\n"
    return f"{header}Subject: {mail.subject}\n\n{mail.body}"


def create_server(state_dir: Path) -> MCPServer[Any]:
    """Build the mail server backed by ``state_dir``."""
    st = store(state_dir)
    server: MCPServer[Any] = MCPServer(
        name=SERVER_NAME,
        instructions="Read the user's email and send email on their behalf.",
    )

    @server.tool()
    def list_emails(folder: Literal["inbox", "sent"] = "inbox") -> str:
        """List emails in a folder ('inbox' or 'sent'), newest last."""
        state = st.load()
        mails = state.inbox if folder == "inbox" else state.outbox
        return "\n".join(_summary(m) for m in mails) if mails else f"No emails in {folder}."

    @server.tool()
    def read_email(email_id: str) -> str:
        """Read the full content of an email by its ID."""
        state = st.load()
        for mail in [*state.inbox, *state.outbox]:
            if mail.id == email_id:
                return _render(mail)
        raise ToolError(f"No email with ID {email_id!r}")

    @server.tool()
    def search_emails(query: str) -> str:
        """Search the inbox for emails whose sender, subject or body contains the query."""
        needle = query.casefold()
        hits = [
            m for m in st.load().inbox if needle in f"{m.sender}\n{m.subject}\n{m.body}".casefold()
        ]
        return "\n".join(_summary(m) for m in hits) if hits else "No matching emails."

    @server.tool()
    def send_email(to: str, subject: str, body: str) -> str:
        """Send an email. 'to' is one address or several separated by commas."""
        recipients = [addr.strip() for addr in to.split(",") if addr.strip()]
        if not recipients:
            raise ToolError("At least one recipient is required")
        with st.update() as state:
            mail = Email(
                id=f"sent-{len(state.outbox) + 1}",
                sender=state.owner or AGENT_IDENTITY,
                to=recipients,
                subject=subject,
                body=body,
            )
            state.outbox.append(mail)
        return f"Email sent to {', '.join(recipients)} (ID {mail.id})."

    return server


def main() -> None:
    """Run the mail server over stdio."""
    run_stdio(create_server)


if __name__ == "__main__":
    main()
