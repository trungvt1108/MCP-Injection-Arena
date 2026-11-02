# Adding a defense

A *defense* is anything that tries to stop a prompt-injection attack from
succeeding while preserving the agent's ability to do the user's task. The arena
runs each defense against the same scenarios and reports attack success rate,
utility, confirmation count and latency.

## The `Defense` interface

Defenses subclass `arena.defenses.base.Defense`. A fresh instance is created for
every run, so per-run state (e.g. a taint set) can live on `self`. A defense can
act at either or both of two levels; the base class is a no-op, so override only
what you use.

**Proxy level** — see only MCP traffic:

```python
def wrap_server(self, params: StdioServerParameters) -> StdioServerParameters: ...
```

Rewrite how a mock server is launched, e.g. to put a filtering proxy process in
front of it. Must return `StdioServerParameters` (a command the runner launches
over stdio).

**In-process hooks** — see the agent loop directly:

```python
def system_prompt(self, prompt: str) -> str: ...
async def on_tool_call(self, call: ToolCall, ctx: DefenseContext) -> Decision: ...
async def on_tool_result(self, result: ToolResult, ctx: DefenseContext) -> ToolResult: ...
async def close(self) -> None: ...
```

- `system_prompt` rewrites the system prompt before the run.
- `on_tool_call` returns `Allow()`, `Deny(reason)`, or `Confirm(reason)`. `Deny`
  blocks the call and returns an error to the model. `Confirm` is auto-answered by
  the configurable simulated user (`--confirm yes|no`) and **counted as a
  confirmation** for the user-confirmation trade-off (RQ3).
- `on_tool_result` may rewrite what the model sees (e.g. redact a secret).
- `ctx` (`DefenseContext`) carries the scenario id, the user task, `tool_names`
  (tool → server), and `history` (earlier tool events this run).

Set two class attributes so results are attributable:

```python
class MyDefense(Defense):
    name = "my_defense"
    version = "1"
```

## Registering a defense

Add it to `DEFENSES` in `arena/defenses/__init__.py`, keyed by `name`, with a
zero-argument factory (usually the class itself). Then `arena run --defense
my_defense` and `arena list` pick it up.

## Built-in defenses

| Name | Kind | What it does |
|------|------|--------------|
| `none` | — | Baseline. Allows everything unchanged. |
| `prompt_hardening` | system prompt | Prepends a defensive security policy telling the model to treat tool content as data, not instructions. Pure instruction-level; a persuasive injection can still talk the model past it. |
| `reference_taint` | in-process hooks | Our own simple value-matching taint tracker. Records distinctive values returned by untrusted/private source tools and blocks (or, in `confirm` mode, asks about) a sink call that would carry one out. |

### `reference_taint`'s deliberate weakness

`reference_taint` matches tainted values only by **exact substring** and by one
level of **base64 or hex decoding**. It does not fold case, strip inserted
separators, undo rot13/URL-encoding, or reassemble split values. That is on
purpose: it is the reference baseline against which RQ2 (how easily value-matching
taint tracking is evaded) is measured. It also tokenizes source text on
non-alphanumeric boundaries, so random secret cores are tainted while structural
values like email addresses and URLs are not — which keeps it from blocking
legitimate work such as replying to the address an email came from.

## Third-party defense adapters (`arena/defenses/external/`)

Adapters wrap published defenses so they can be compared on the same scenarios.
The policy, from `CLAUDE.md`, is: **do not invent third-party APIs** — read the
real source, pin the version, and if an API (or how it integrates) cannot be
verified, stop and leave a precise TODO. Each adapter module records `NAME`,
`PACKAGE`, `PINNED_VERSION`, `LICENSE`, `STATUS`, and a `build()` that raises
`NotImplementedError` with what remains, until it is genuinely integrated.
`arena.defenses.external.ADAPTERS` enumerates them.

Status as researched on 2026-11-02:

| Adapter | Package (pin) | License | Status | Blocker |
|---------|---------------|---------|--------|---------|
| `fides` | `agent-framework` (core ≥ 1.3.0) | MIT | pending | FIDES runs inside Microsoft Agent Framework's own agent loop with a real chat client; it needs a **runner backend**, not a `Defense` hook. |
| `mcpkernel` | `mcpkernel==0.3.0` | Apache-2.0 | pending | MCPKernel proxies over **HTTP** (`mcpkernel serve`, URL upstreams); `wrap_server` returns stdio params. Needs an HTTP-server transport in the harness. |
| `sluice` | *unresolved* | ? | pending | "Sluice" names several unrelated projects (`sluice-mcp`, `sluice-taint`, `mcp-sluice`); the intended one must be identified first. |

Each module's docstring holds the verified API details and a numbered list of
exactly what to check before enabling it. None are registered in `DEFENSES` yet,
so `arena run --defense fides` reports an unknown defense by design.

### FIDES — verified entry points (for the future runner backend)

- Install `pip install agent-framework` (FIDES is experimental in
  `agent-framework-core`, Python-only, since v1.3.0).
- `from agent_framework.security import SecureAgentConfig, SecureMCPToolProxy,
  quarantined_llm, ContentLabel, IntegrityLabel, ConfidentialityLabel`.
- `SecureAgentConfig(...)` is a context provider attached to an
  `agent_framework.Agent`; sinks are `@tool`s annotated with
  `accepts_untrusted=False` / `max_allowed_confidentiality="public"`.
- Paper: Costa et al., *FIDES* (2025), arXiv:2505.23643.

```bibtex
@misc{costa2025fides,
  title         = {Securing {AI} Agents with Information-Flow Control},
  author        = {Costa, Manuel and others},
  year          = {2025},
  eprint        = {2505.23643},
  archivePrefix = {arXiv},
  primaryClass  = {cs.CR},
  note          = {FIDES; implemented in Microsoft Agent Framework agent\_framework.security}
}
```

## Testing a defense

- Unit-test the hooks directly (see `tests/test_defenses.py`): feed `on_tool_result`
  a source result, then assert `on_tool_call` blocks/allows the right sink calls.
- Add an end-to-end check with `run_experiment(model="mock", defense="...")` on a
  scenario whose `mock_trajectory` performs the attack, and assert the expected
  `attack_success` / `utility_success` and tool-call decisions.
- Tests must not touch the network; third-party adapters that aren't installed
  must be exercised against a fake module (see `tests/test_external_templates.py`
  for the pattern) or left asserting that `build()` raises.
