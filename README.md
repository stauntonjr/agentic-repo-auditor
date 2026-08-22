# Agentic Repo Auditor

Agentic Repo Auditor is a read-only Python CLI that turns observable repository state into deterministic, evidence-backed JSON and Markdown reports. It is intended for maintainers of agent-developed repositories and engineering leads evaluating whether a repository has enough governance, verification, security configuration, and agent context to support reliable work.

This is an early `0.1.0` implementation. It assesses repository engineering signals; it does not claim to understand the full application or prove compliance.

## What it checks

The first report covers six categories:

- governance: repository instructions, machine-readable project contract, and community files;
- Git: clean or outstanding worktree state;
- CI: workflow presence and immutable external Action references;
- security: reporting policy, dependency updates, and visible CodeQL configuration;
- testing: an authoritative check contract and conventional automated tests; and
- agent readiness: instruction coverage and portable `SKILL.md` structure.

Every finding has a stable ID, status, severity, description, source evidence, and remediation. The report does not collapse unlike evidence into an opaque numeric grade.

## Install and run

The project currently supports Python 3.11 and newer.

```bash
uv sync --locked
uv run agentic-repo-auditor --version
uv run agentic-repo-auditor audit /path/to/repository --format markdown
uv run agentic-repo-auditor audit /path/to/repository --format json
```

Output is written to standard output. Redirect it to a location you choose; the auditor does not intentionally write to the target repository.

Exit statuses are part of the public CLI contract:

- `0`: the command completed and no finding met the configured failure threshold;
- `1`: at least one finding met the `--fail-on` threshold; and
- `2`: the target, configuration, or command input was invalid.

The default threshold is `fail`. Use `--fail-on warn` for a stricter policy or `--fail-on none` for advisory-only execution.

## Configuration

Configuration is optional JSON:

```json
{
  "schema_version": "1.0",
  "disabled_checks": ["git.clean-worktree"]
}
```

Run with `--config path/to/config.json`. Unknown keys and unknown check IDs fail closed. The versioned schema is [repository-audit-config.schema.json](schemas/repository-audit-config.schema.json).

## Report contract

JSON is the canonical machine representation. Markdown is generated deterministically from the same model. The report contains:

- schema and tool versions;
- repository name, Git revision, branch, dirty state, and deterministic state identity;
- active configuration;
- fixed-order summary counts; and
- findings sorted by stable ID with sorted evidence.

The schema is [repository-audit-report.schema.json](schemas/repository-audit-report.schema.json). Wall-clock timestamps and absolute target paths are deliberately omitted so repeated audits of the same state are byte-identical and disclose less local information.

## Development

The authoritative local and CI boundary is:

```bash
make smoke
```

Useful focused commands:

```bash
uvx --from ruff==0.12.10 ruff format --check .
uvx --from ruff==0.12.10 ruff check .
uvx --from pyright==1.1.403 pyright
uv run --with pytest==8.4.1 python -m pytest tests/test_auditor.py tests/test_auditor_cli.py
python3 scripts/package_smoke.py
```

The repository includes the agentic engineering harness that governs intake, sources of truth, architecture decisions, write scopes, independent verification, GitHub planning, and reporting. Start with [AGENTS.md](AGENTS.md), [the project contract](harness/project.yaml), and [the handoff](docs/project/handoff.md).

## Deliberate boundaries

The offline core does not:

- mutate audited repositories or GitHub;
- execute remediation;
- call models or score model output;
- infer privileged GitHub settings from files;
- replace OpenSSF Scorecard, OSPS Baseline assessment, or language-specific scanners;
- emit SARIF yet; or
- assess full application behavior, architecture, data flow, runtime health, or product completeness.

That last need is valuable but belongs to a companion full-application assessment product. The research and proposed architecture decision are in [repository-auditor-landscape.md](docs/research/repository-auditor-landscape.md) and [ADR-0006](docs/adr/0006-repository-audit-finding-model.md).

## Security and privacy

Repository paths and configuration can be sensitive. The core runs locally, has no runtime dependencies, and performs no network calls. Git inspection disables repository-configured filesystem monitors, hooks, content-filter drivers, optional locks, and lazy object fetching, including filter names discovered in registered submodules. Evidence collection does not follow repository symlinks, and the state ID fingerprints dirty index/worktree content plus nested Git HEAD, staged entries, and hidden index flags rather than only path names. Reports intentionally omit absolute target paths, but evidence can still reveal filenames and security gaps. Treat reports according to the source repository's classification.

Report vulnerabilities using [SECURITY.md](SECURITY.md). The project is licensed under MIT; see [LICENSE](LICENSE).
