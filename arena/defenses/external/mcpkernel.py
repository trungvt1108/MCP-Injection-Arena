"""Adapter (pending) for MCPKernel, a security gateway/proxy for MCP tool servers.

Status: NOT YET INTEGRATED. The package and API are verified; the blocker is that
MCPKernel proxies over HTTP, while the arena launches servers over stdio and
``Defense.wrap_server`` can only return ``StdioServerParameters``. ``build()``
raises with the exact integration path.

What MCPKernel is (verified 2026-11-02 from
https://github.com/piyushptiwari1/mcpkernel and its README):

* A gateway that sits between the agent and MCP tool servers, enforcing policy on
  every call, with taint tracking and sandboxed execution.
* Install ``pip install mcpkernel`` (``mcpkernel[all]`` for all backends).
  License Apache-2.0. Researched version: 0.3.0 (2026-05-25).
* Gateway is HTTP: ``mcpkernel serve --host 127.0.0.1 --port 8000`` exposes
  ``http://localhost:8000/mcp``; upstreams are configured by URL + transport
  (e.g. ``transport: streamable_http``). Python API:
  ``MCPKernelProxy(upstream=["http://..."], policy="strict", taint=True)``.
* ``mcpkernel mcp-serve`` runs MCPKernel itself as a stdio MCP server exposing its
  *security tools* - it does NOT wrap another stdio server transparently.

Why it is not a drop-in ``wrap_server`` proxy:

* ``wrap_server`` must return ``StdioServerParameters`` (a command to launch). The
  README documents no stdio-to-stdio pass-through: upstreams are HTTP URLs.

TODO (to integrate; verify each against the installed package, do not guess):
  1. Teach the harness to target HTTP servers (a ``ServerTarget`` that is a URL),
     then run each mock server over streamable-http (our servers already support
     ``MCPServer.run("streamable-http")``) instead of stdio for this defense.
  2. Launch ``mcpkernel serve`` with an upstream config pointing at those URLs, and
     point the arena's ``Client`` at the gateway URL. Manage the gateway process
     lifetime for the run (start/stop), since it is out-of-process.
  3. Confirm the exact ``policy`` values and ``taint`` semantics, and whether
     ``MCPKernelProxy`` can be used in-process instead of the ``serve`` daemon.
  4. Pin ``mcpkernel==0.3.0`` (or the version tested) on the registered defense.
"""

from __future__ import annotations

from typing import NoReturn

NAME = "mcpkernel"
PACKAGE = "mcpkernel"
PINNED_VERSION = "0.3.0"
LICENSE = "Apache-2.0"
STATUS = "pending-http-transport"


def build() -> NoReturn:
    """Raise: MCPKernel is HTTP-only; wrap_server returns stdio. See module docstring."""
    raise NotImplementedError(
        "MCPKernel is not yet integrated. It is an HTTP gateway (mcpkernel serve, "
        "URL upstreams), but Defense.wrap_server returns StdioServerParameters and "
        "the arena runs servers over stdio. Integrate by serving the mock servers "
        "over streamable-http and pointing a gateway at them (see the numbered TODO "
        "in arena/defenses/external/mcpkernel.py). Pin mcpkernel==0.3.0."
    )
