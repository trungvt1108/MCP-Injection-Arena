"""MCP Injection Arena: a reproducible benchmark for prompt-injection defenses in MCP agents."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("mcp-injection-arena")
except PackageNotFoundError:  # pragma: no cover - only when running from a raw checkout
    __version__ = "0.0.0+unknown"

__all__ = ["__version__"]
