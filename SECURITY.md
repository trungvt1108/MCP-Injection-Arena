# Security Policy

MCP Injection Arena evaluates other people's security tools. That means we will
sometimes find working bypasses for real defenses. This document explains how we
handle that, and how to report problems in the arena itself.

## Scope and safety guarantees

- All experiments run in a local sandbox (Docker or temporary directories). The
  arena never contacts real third-party services, email, GitHub or payment APIs.
- All "secrets" used in scenarios are randomly generated canary tokens. No real
  credentials are ever used or collected.
- Attack payloads are designed to trigger deterministic, harmless checks (a canary
  string reaching a mock sink, a file deleted inside a temp directory). They are
  not intended to be weaponised against production systems.

## Responsible disclosure to defense authors

When the benchmark finds a bypass that is **specific to a defense** (not just a
generic weakness already documented in its README or paper), we follow this process:

1. **Private notice.** Before publishing, we contact the defense's maintainers
   through their documented security channel (their `SECURITY.md`, GitHub private
   vulnerability reporting, or a maintainer email). We send the scenario, the
   payload, the transcript and the exact version tested.
2. **Embargo.** We give maintainers **90 days** to respond and, if they choose,
   release a fix. We can extend this on request if a fix is in progress.
3. **Leaderboard handling.** During the embargo, results for that defense are
   published only in aggregate, without the specific payloads or transcripts that
   demonstrate the bypass.
4. **Publication.** After a fix is released or the embargo ends, we publish the full
   scenario and results. If a fix exists, we re-run against the fixed version and
   report both versions.
5. **Credit and right of reply.** Maintainers may give a short statement, which we
   link from the leaderboard entry for their defense.

Generic attack classes (for example "value-matching taint tracking misses base64
encoded data") are research findings rather than vulnerabilities in a single
product. We publish them without embargo, but we still tell affected maintainers
before publication when we can.

## Reporting a vulnerability in the arena

Examples: a scenario or mock server that can reach the real network, a sandbox
escape, a judge that can be fooled into reporting a false result, or leaked
non-canary data in a results file.

Please **do not open a public issue**. Instead, use GitHub's
[private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability)
on this repository.
<!-- TODO: add a maintainer contact address as a fallback once the repository is public. -->

We aim to acknowledge reports within 7 days.

## Reporting a bypass of a defense we evaluate

If you find a bypass of a third-party defense, report it to that project first,
following its own security policy. You are welcome to contribute the scenario here
afterwards, and we will follow the embargo process above.
