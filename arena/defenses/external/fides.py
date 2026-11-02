"""Adapter (pending) for Microsoft FIDES (``agent_framework.security``).

FIDES is Microsoft Agent Framework's information-flow-control defense.

Status: NOT YET INTEGRATED. The FIDES API is verified against Microsoft's docs
(below); what is missing is a *runner backend*, because FIDES does not fit the
arena's :class:`~arena.defenses.base.Defense` hook shape. ``build()`` raises with
the exact integration path and what remains to confirm.

What FIDES is (verified 2026-11-02 from
https://learn.microsoft.com/en-us/agent-framework/agents/security and
https://github.com/microsoft/agent-framework discussion #5624 / PR #5331):

* Planner-level information-flow control: every ``Content`` item carries an
  integrity (trusted/untrusted) and confidentiality (public/private/user_identity)
  label; labels propagate through tool calls; a sink is blocked *before* it runs
  when the context label exceeds what the sink declares it accepts.
* Ships in ``agent-framework-core`` (install ``pip install agent-framework``),
  experimental, since core v1.3.0, Python-only. Based on the FIDES paper, Costa
  et al. 2025 (arXiv:2505.23643).
* Public API (import from ``agent_framework.security``): ``SecureAgentConfig``,
  ``quarantined_llm``, ``store_untrusted_content``, ``inspect_variable``,
  ``ContentLabel``, ``IntegrityLabel``, ``ConfidentialityLabel``,
  ``rewritten_arguments``, and ``SecureMCPToolProxy`` for MCP tools.
* Wiring: ``SecureAgentConfig(...)`` is a *context provider* attached to an
  ``agent_framework.Agent(client=<ChatClient>, tools=[...],
  context_providers=[config])``. Sinks are ``@tool`` functions annotated via
  ``additional_properties`` (``accepts_untrusted=False``,
  ``max_allowed_confidentiality="public"``). Enforcement modes: hard block
  (``block_on_violation=True``), human-in-the-loop (``approval_on_violation=True``),
  or dry run (``enable_policy_enforcement=False``).

Why it is not a drop-in :class:`Defense`:

* FIDES runs *inside* Agent Framework's own agent loop and requires an
  ``agent_framework`` ``ChatClient`` (e.g. ``FoundryChatClient``/OpenAI). The arena
  drives its own LiteLLM loop against stdio MCP servers, so FIDES cannot be
  expressed as ``wrap_server`` / ``on_tool_call`` hooks.

TODO (to integrate; each item must be checked against the installed package, do
not guess):
  1. Add a FIDES *runner backend* alongside ``arena.agent.runner``: build an
     ``agent_framework.Agent`` whose tools are the arena's mock MCP servers via
     ``SecureMCPToolProxy`` (verify its constructor and ``trust_server_ifc``
     default), with a real ``ChatClient``; FIDES cannot run against the mock LLM.
  2. Map each arena sink tool to the right annotation: outbound tools
     (http_post, send_message, send_email, add_comment, create_issue, fetch_url,
     run_command) -> ``max_allowed_confidentiality="public"`` and/or
     ``accepts_untrusted=False``; secret sources (read_file on .env etc.) ->
     ``confidentiality="private"``. Confirm the exact ``additional_properties``
     keys against the installed version.
  3. Decide the mapping from FIDES block/approval outcomes to the arena's
     Allow/Deny/Confirm accounting so confirmations are counted for RQ3.
  4. Pin the exact ``agent-framework`` version once integrated (floor:
     agent-framework-core >= 1.3.0) and record it on the registered defense.
"""

from __future__ import annotations

from typing import NoReturn

NAME = "fides"
PACKAGE = "agent-framework"
PINNED_VERSION = "agent-framework-core>=1.3.0"  # FIDES experimental; pin exact on integration
LICENSE = "MIT"  # microsoft/agent-framework
CITATION = "costa2025fides"  # arXiv:2505.23643
STATUS = "pending-runner-backend"


def build() -> NoReturn:
    """Raise: FIDES needs a runner backend, not a Defense hook. See module docstring."""
    raise NotImplementedError(
        "FIDES is not yet integrated. Its API is verified (agent_framework.security: "
        "SecureAgentConfig, SecureMCPToolProxy), but it runs inside Microsoft Agent "
        "Framework's own agent loop with a real ChatClient and cannot be expressed as "
        "an arena Defense hook. Integrate it as a separate runner backend (see the "
        "numbered TODO in arena/defenses/external/fides.py); pin the exact "
        "agent-framework version then. Cite costa2025fides (arXiv:2505.23643)."
    )
