"""Import attack templates from published indirect-prompt-injection suites.

The point of this module is comparability: run the *same* arena scenarios with a
real published attack family instead of the neutral ``placeholder/default``
stand-in, and have every result record which family it used.

Design rules (see also ``docs/CITATIONS.md``):

* **No payload prose is vendored here.** Each adapter loads the persuasive text
  at run time from the suite's *own installed package*, so the suite's license
  governs its own text. We only ship the adapter code and attribution metadata.
* **Verified, not guessed.** An adapter is only enabled once the exact location
  of the templates in the installed package, and the suite's license, have been
  checked against the real source. Unverified suites raise ``NotImplementedError``
  describing precisely what to confirm, rather than loading something uncertain.
* Every registered template records ``source``, ``license``, ``citation`` (a key
  in ``docs/CITATIONS.md``) and the installed ``version``.

Enabled today:

* ``agentdojo/important_instructions`` - AgentDojo (MIT), loaded at run time from
  the installed ``agentdojo`` package. Verified against agentdojo 0.1.35.

Pending verification (adapters raise with instructions): InjecAgent, BIPIA.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

from arena.attacks.templates import AttackTemplate, register

CITATIONS = {
    "agentdojo": "debenedetti2024agentdojo",
    "injecagent": "zhan2024injecagent",
    "bipia": "yi2024bipia",
}
"""Map suite name -> BibTeX key in docs/CITATIONS.md."""


def _installed_version(package: str) -> str:
    try:
        return _pkg_version(package)
    except PackageNotFoundError:
        return ""


def register_agentdojo(*, replace: bool = False) -> list[AttackTemplate]:
    """Register AgentDojo's ``important_instructions`` jailbreak as a template.

    The payload text is read at run time from the installed MIT-licensed
    ``agentdojo`` package (class attribute
    ``ImportantInstructionsAttack._JB_STRING``, formatted with ``{user}``,
    ``{model}`` and ``{goal}`` - verified against agentdojo 0.1.35). Nothing is
    copied into this repository.

    Returns:
        The registered template(s), or ``[]`` if ``agentdojo`` is not installed.
    """
    try:
        from agentdojo.attacks.base_attacks import (  # type: ignore[import-not-found]
            DEFAULT_MODEL_NAME,
            DEFAULT_USER_NAME,
        )
        from agentdojo.attacks.important_instructions_attacks import (  # type: ignore[import-not-found]
            ImportantInstructionsAttack,
        )
    except ImportError:
        return []

    jailbreak: str = ImportantInstructionsAttack._JB_STRING

    def render(goal: str) -> str:
        try:
            return jailbreak.format(user=DEFAULT_USER_NAME, model=DEFAULT_MODEL_NAME, goal=goal)
        except (KeyError, IndexError) as exc:
            raise RuntimeError(
                "agentdojo ImportantInstructionsAttack._JB_STRING changed its "
                "placeholders; update arena.attacks.templates.external.register_agentdojo"
            ) from exc

    template = AttackTemplate(
        ref="agentdojo/important_instructions",
        family="agentdojo",
        variant="important_instructions",
        render=render,
        source="agentdojo",
        description="AgentDojo 'important_instructions' jailbreak, loaded from the package.",
        license="MIT",
        citation=CITATIONS["agentdojo"],
        version=_installed_version("agentdojo"),
    )
    return [register(template, replace=replace)]


def register_injecagent(*, replace: bool = False) -> list[AttackTemplate]:
    """Not yet enabled. Verify the items below against the real source first.

    Raises:
        NotImplementedError: Always, with what must be checked.
    """
    raise NotImplementedError(
        "InjecAgent adapter is not enabled. Before enabling, verify against "
        "github.com/uiuc-kang-lab/InjecAgent: (1) the license - no LICENSE file was "
        "found at the default-branch root (checked 2026-11-02), so its terms must be "
        "confirmed before its text may be loaded or vendored; (2) the JSONL schema of "
        "data/attacker_cases_ds.jsonl and data/attacker_cases_dh.jsonl, i.e. the field "
        "holding the attacker instruction and the 'enhanced'/hacking-prompt prefix. "
        "Then load from a local clone at run time (e.g. an ARENA_INJECAGENT_DIR path) "
        "and map that field to a Renderer. Do not vendor the text. "
        f"Cite {CITATIONS['injecagent']!r} (arXiv:2403.02691)."
    )


def register_bipia(*, replace: bool = False) -> list[AttackTemplate]:
    """Not yet enabled. Verify the items below against the real source first.

    Raises:
        NotImplementedError: Always, with what must be checked.
    """
    raise NotImplementedError(
        "BIPIA adapter is not enabled. The microsoft/BIPIA *code* is MIT, but the "
        "repository states its benchmark datasets carry their own licenses, so the "
        "attack text's license must be confirmed before loading or vendoring. Before "
        "enabling, verify: (1) the path to the attack templates under benchmark/ "
        "(reported as files such as text_attack_test.json - confirm the exact path and "
        "the field holding each attack string); (2) whether BIPIA is importable as a "
        "package or only available as a cloned repo. Then load at run time from a local "
        "clone (e.g. an ARENA_BIPIA_DIR path). Do not vendor the text. "
        f"Cite {CITATIONS['bipia']!r} (arXiv:2312.14197)."
    )


def register_external_suites(*, replace: bool = False) -> list[AttackTemplate]:
    """Register every *verified* external suite whose package is installed.

    Only AgentDojo is verified today; it is skipped silently if not installed.
    InjecAgent and BIPIA are intentionally not called here - enable them via their
    own functions once their TODOs are resolved.
    """
    return register_agentdojo(replace=replace)


__all__ = [
    "CITATIONS",
    "register_agentdojo",
    "register_bipia",
    "register_external_suites",
    "register_injecagent",
]
