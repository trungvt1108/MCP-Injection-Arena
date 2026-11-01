
# Project: MCP Injection Arena

## Mission

An open, reproducible benchmark and public leaderboard that measures how well
prompt-injection defenses for MCP-based AI agents actually work. We are the
"referee", not another defense tool. The deliverables are: (1) a benchmark
harness, (2) a scenario + attack suite, (3) adapters for existing defenses,
(4) a static leaderboard site, (5) data for a research paper.

## Research questions

- RQ1: How do proxy-level MCP defenses (see only tool calls) compare with
  planner-level IFC defenses (e.g. FIDES, CaMeL)?
- RQ2: How easily is value-matching taint tracking evaded when the agent
  transforms data (paraphrase, encoding, splitting, side channels)?
- RQ3: What is the security / utility / user-confirmation trade-off of each defense?

## Hard rules (ethics & safety)

- Everything runs in a local sandbox (Docker or temp dirs). NEVER contact real
  third-party services, real email, real GitHub, or real payment APIs.
- All "secrets" are randomly generated canary tokens, never real credentials.
- Tests must not make network calls. LLM calls in tests use a scripted mock LLM.
- Add SECURITY.md describing responsible disclosure to defense authors.

## Architecture

mcp-injection-arena/
  arena/
    cli.py              # Typer CLI: `arena run`, `arena list`, `arena report`
    config.py           # pydantic settings
    canary.py           # canary token generation + detection in any encoding
    scenarios/
      schema.py         # pydantic models for scenario YAML
      loader.py
      data/             # scenario YAML files, grouped by category
    servers/            # mock MCP servers built with the official `mcp` Python SDK (FastMCP)
      filesystem.py     # sandboxed temp dir, contains canary files like .env
      mail.py           # in-memory inbox/outbox
      web.py            # serves local fixture pages (may contain injections)
      issues.py         # GitHub-like issues/PRs/comments
      sink.py           # outbound channels: http_post, send_message (records everything)
    agent/
      runner.py         # tool-calling agent loop via LiteLLM (any provider + Ollama)
      mock_llm.py       # scripted LLM for deterministic tests
    defenses/
      base.py           # Defense interface
      none.py           # baseline: no defense
      prompt_hardening.py
      reference_taint.py  # our own simple value-matching taint proxy (reference baseline)
      external/         # adapters for third-party tools (Sluice, MCPKernel, FIDES...)
    attacks/
      level1_direct.py  # injections in issues, emails, web pages
      level2_evasion.py # paraphrase, base64/hex/rot13, char splitting, side channels, chunking
      level3_adaptive.py# attacker LLM that reads block reasons and mutates payloads
    judges/
      checks.py         # deterministic success checks (see below)
    metrics.py          # ASR, utility, confirmations, latency, 95% CI
    report.py           # JSON results -> markdown tables + leaderboard data
  site/                 # static leaderboard (GitHub Pages), reads results/*.json
  results/              # versioned result files
  tests/
  docs/                 # adding-a-defense.md, adding-a-scenario.md, threat-model.md

## Key design decisions

- Scenario = user_task + environment fixtures + injection (location + payload)
  + attack_goal check + utility check. Defined in YAML, validated by pydantic.
- Judges are DETERMINISTIC, never an LLM. Attack goal types:
  `canary_exfil` (canary appears in any sink, after decoding base64/hex/rot13/url,
  stripped separators, case-folded), `file_deleted`, `command_executed`,
  `tool_called_with` (tool name + argument predicate).
  Utility check types: `file_contains`, `message_sent_to`, `answer_contains`.
- Defense interface supports two kinds:
  1. proxy defenses: `wrap_server(params: StdioServerParameters) -> StdioServerParameters`
  2. in-process defenses: hooks `on_tool_call(call, ctx) -> Allow | Deny(reason) | Confirm(reason)`
     and `on_tool_result(result, ctx) -> result`.
     `Confirm` is auto-answered by a configurable simulated user (always-yes /
     always-no) and counted as a confirmation.
- Every run records: model, defense name + version, scenario id, seed, full
  transcript (JSONL), tool calls, decisions, latency. Results are reproducible
  with one command.
- Each (scenario, defense, model) is repeated N times (default 3); report mean and 95% CI.

## Tech & quality

- Python 3.11+, `uv` for env, `ruff` + `mypy --strict` on arena/, `pytest`.
- GitHub Actions: lint, type-check, tests on every PR.
- License: Apache-2.0. Type hints and docstrings on public APIs.
- Do not invent third-party APIs. If unsure how Sluice/MCPKernel/FIDES/etc. work,
  read their docs/source or leave a clearly marked TODO with what must be verified.

## How to work

- Work one phase at a time. At the end of each phase: run ruff, mypy, pytest;
  fix failures; summarize what was done and what is left.
- Prefer small, readable modules. Ask before adding heavy dependencies.
