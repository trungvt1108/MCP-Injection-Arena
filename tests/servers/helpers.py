"""Helpers for driving mock servers through a real MCP client, in-process."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mcp import Client
from mcp.server.mcpserver import MCPServer
from mcp.types import CallToolResult, TextContent


@dataclass
class ToolResult:
    text: str
    is_error: bool


def to_result(result: CallToolResult) -> ToolResult:
    text = "\n".join(c.text for c in result.content if isinstance(c, TextContent))
    return ToolResult(text=text, is_error=bool(result.is_error))


async def call(server: MCPServer[Any], tool: str, **arguments: Any) -> ToolResult:
    async with Client(server) as client:
        return to_result(await client.call_tool(tool, arguments))


async def tool_names(server: MCPServer[Any]) -> set[str]:
    async with Client(server) as client:
        return {t.name for t in (await client.list_tools()).tools}
