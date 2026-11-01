# Contributing to MCP Injection Arena

Thanks for helping. The goal of this project is to be a fair, reproducible referee
for prompt-injection defenses. Contributions of scenarios, attacks, defense adapters
and fixes are all welcome.

## Ground rules

These rules are not negotiable. Pull requests that break them will not be merged.

- **Sandbox only.** Code must never contact real third-party services, real email,
  real GitHub or real payment APIs. Everything runs against the mock MCP servers in
  `arena/servers/`.
- **Canary tokens only.** Every "secret" is a randomly generated canary from
  `arena/canary.py`. Never put real credentials in fixtures, tests or results.
- **No network in tests.** LLM calls in tests use the scripted mock LLM. The test
  suite blocks non-loopback sockets, so a test that hits the network will fail.
- **Deterministic judges.** Attack success and utility are decided by code, never by
  an LLM.
- **Do not invent third-party APIs.** If you are unsure how an external defense works,
  read its docs or source, or leave a clearly marked `TODO` saying what must be checked.
- **Disclosure.** If your contribution demonstrates a new bypass of a specific
  defense, read [SECURITY.md](SECURITY.md) before opening a public PR.

## Development setup

You need Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync                 # create .venv and install the package and dev tools
uv run arena --help     # check the CLI works
```

## Checks

CI runs exactly these commands. Run them before opening a PR:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy             # strict mode, on arena/
uv run pytest
```

`uv run ruff format .` and `uv run ruff check --fix .` fix most style issues.

## Code style

- Small, readable modules.
- Type hints and docstrings on every public function, class and module
  (`mypy --strict` and ruff's pydocstyle rules enforce this).
- Ask in an issue before adding a heavy dependency.

## Adding a scenario or a defense

Step-by-step guides will live in `docs/adding-a-scenario.md` and
`docs/adding-a-defense.md`. They will be written once the scenario schema and the
defense interface are in place.

## Pull requests

- Keep each PR focused on one change.
- Include tests for new behaviour.
- If you add or change a scenario, attack or defense, say in the description how it
  affects existing results.

By contributing, you agree that your contributions are licensed under the
[Apache-2.0 license](LICENSE).
