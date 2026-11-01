# MCP Injection Arena

**An open, reproducible benchmark and public leaderboard for prompt-injection defenses in MCP-based AI agents.**

> Status: pre-alpha. The harness is being built; there are no results yet.

## Why this exists

Agents that use the [Model Context Protocol](https://modelcontextprotocol.io) read
untrusted content (issues, emails, web pages, files) and also have tools that can
act on the world. A growing number of tools claim to stop prompt injection in this
setting, but each is evaluated on its own scenarios, with its own attacks and its
own definition of success. That makes them hard to compare.

MCP Injection Arena is a **referee, not another defense**. It provides:

1. **A benchmark harness**: a tool-calling agent loop running against mock MCP
   servers in a local sandbox.
2. **A scenario and attack suite**: realistic user tasks with injected content, from
   direct injections to encoding and splitting evasions and adaptive attackers.
3. **Adapters for existing defenses**: both proxy-level (they see only tool calls)
   and planner-level information-flow control.
4. **Deterministic judges**: attack success and task utility are checked by code
   (canary tokens, file state, tool-call predicates), never by an LLM.
5. **A static leaderboard**: security, utility and user-confirmation cost, with
   95% confidence intervals.

Research questions:

- **RQ1:** How do proxy-level MCP defenses compare with planner-level IFC defenses?
- **RQ2:** How easily is value-matching taint tracking evaded when the agent
  transforms data (paraphrase, encoding, splitting, side channels)?
- **RQ3:** What is the security / utility / user-confirmation trade-off of each defense?

Everything runs locally. No real third-party services are contacted, and every
"secret" is a randomly generated canary token.

## Quickstart

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run arena list                                   # scenarios and defenses

# Offline smoke test: replays each scenario's scripted "compromised agent"
uv run arena run --model mock --defense none --repeats 1

# A real model, via any LiteLLM provider (Ollama runs fully locally)
uv run arena run --model ollama/llama3.1 --defense none --scenario all --repeats 3
```

Each run writes `results/<timestamp>.json`, plus one JSONL transcript per run in
`results/<timestamp>/`.

## Leaderboard

> TODO: link to the GitHub Pages leaderboard once the first results are published.

| Defense | Kind | Attack success rate ↓ | Utility ↑ | Confirmations ↓ |
|---------|------|----------------------:|----------:|----------------:|
| *no results yet* | | | | |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). To report a vulnerability, in the arena or
in a defense we evaluate, see [SECURITY.md](SECURITY.md).

## Citation

> TODO: replace with the paper reference once it is available.

```bibtex
@misc{mcpinjectionarena,
  title        = {MCP Injection Arena: A Reproducible Benchmark for Prompt-Injection Defenses in MCP Agents},
  author       = {TODO},
  year         = {TODO},
  howpublished = {\url{TODO}}
}
```

## License

[Apache-2.0](LICENSE)
