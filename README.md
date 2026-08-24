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

Agent-instruction coverage is deliberately lexical and explainable rather than model-scored. It
tokenizes `AGENTS.md` and checks a documented bounded vocabulary for source or authority,
testing, safety, and verification. Equivalent terms such as `authoritative` may satisfy a signal;
the report records the exact matched term. This does not prove that the instructions are correct,
complete, or followed.

The recognized lowercase word tokens and bounded structures are fixed in four groups:

- source or authority: `source`, `sources`, `authority`, `authoritative`, `precedence`;
- testing: `test`, `tests`, `testing`;
- safety: `safe`, `safely`, `safety`, or the prohibition token `never` followed within the next
  five tokens of the same punctuation-bounded clause by `confidential` or `proprietary` and then
  `data` in that same window; and
- verification: `verify`, `verified`, `verification`, `validate`, `validation`.

For the bounded confidentiality structure, evidence records the exact matched tokens, such as
`safety:never+confidential+data`. A broad `never`, `security`, or `authority` token does not satisfy
the safety signal by itself.

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

Schema 1.1 adds portable evidence declarations. A general repository may declare a safe
repository-relative JSON or YAML project contract:

```json
{
  "schema_version": "1.1",
  "evidence": {
    "project_contract": {"path": "docs/project-contract.yaml"}
  }
}
```

If a machine-readable project contract is genuinely not applicable, record the disposition rather
than disabling the finding:

```json
{
  "schema_version": "1.1",
  "evidence": {
    "project_contract": {
      "not_applicable_reason": "This repository contains one immutable policy document and delegates no project authority."
    }
  }
}
```

`harness/project.yaml` remains automatic evidence when no declaration is configured. Configured
paths must be normalized repository-relative `.json`, `.yaml`, or `.yml` paths to bounded UTF-8,
non-symlink regular files containing a non-empty object. Missing, malformed, escaping, or symlinked
configured evidence fails closed with exit status 2. Explicit dispositions appear as
`not-applicable` findings with the exact reason; they do not remove the finding.

Run with `--config path/to/config.json`. Schema 1.0 remains accepted without evidence declarations.
Unknown keys, unsupported evidence declarations, and unknown check IDs fail closed. The versioned schema is
[repository-audit-config.schema.json](schemas/repository-audit-config.schema.json); the decision
boundary is recorded in [ADR-0007](docs/adr/0007-portable-evidence-declarations.md).

Schema 1.2 adds a portable authoritative primary-check declaration with repository provenance:

```json
{
  "schema_version": "1.2",
  "evidence": {
    "primary_check": {
      "command": "make check",
      "source": "Makefile"
    }
  }
}
```

`source` must be a normalized repository-relative path to a non-empty, bounded UTF-8 regular file;
symlink components, `.git`, and path traversal are rejected. The source is maintainer-declared
provenance, not a claim that the auditor semantically interprets the file. The auditor records but
never executes `command`. Empty, multiline, unbalanced, disposition-shaped, and obvious successful
no-op commands fail closed. A primary check may instead use `not_applicable_reason`, with the same
bounded disposition rules as project-contract evidence.

Without a configured declaration, the auditor retains automatic
`harness/project.yaml` compatibility. It does not infer authority from README prose, CI presence,
Makefile targets, package scripts, or other filenames. The exact command and source, exact
disposition reason, or automatic-detection state appears in both report formats. See
[ADR-0008](docs/adr/0008-portable-primary-check-declarations.md).

## Report contract

JSON is the canonical machine representation. Markdown is generated deterministically from the same model. The report contains:

- schema and tool versions;
- repository name, Git revision, branch, dirty state, and deterministic state identity;
- active configuration;
- fixed-order summary counts; and
- findings sorted by stable ID with sorted evidence.

Report schema 1.2 includes normalized project-contract and primary-check evidence. The schema is
[repository-audit-report.schema.json](schemas/repository-audit-report.schema.json). Wall-clock
timestamps and absolute target paths are deliberately omitted so repeated audits of the same state
are byte-identical and disclose less local information.

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

That last need is valuable but belongs to a companion full-application assessment product. The research and accepted architecture decision are in [repository-auditor-landscape.md](docs/research/repository-auditor-landscape.md) and [ADR-0006](docs/adr/0006-repository-audit-finding-model.md).

## Security and privacy

Repository paths and configuration can be sensitive. The core runs locally, performs no network calls, and has one pinned runtime dependency: PyYAML for semantic parsing of untrusted workflow and Skill metadata under input-size, node-count, and depth limits. Git inspection disables repository-configured filesystem monitors, hooks, content-filter drivers, optional locks, and lazy object fetching, including filter names discovered in registered submodules. Evidence collection does not follow repository symlinks, and the state ID fingerprints dirty index/worktree content plus nested Git HEAD, staged entries, and hidden index flags rather than only path names. Reports intentionally omit absolute target paths, but evidence can still reveal filenames and security gaps. Treat reports according to the source repository's classification.

Report vulnerabilities using [SECURITY.md](SECURITY.md). The project is licensed under MIT; see [LICENSE](LICENSE).
