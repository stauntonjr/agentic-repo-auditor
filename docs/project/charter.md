# Project charter

Status: active

## Purpose

A read-only Python CLI for repository maintainers that produces evidence-backed engineering-harness, security, CI, governance, and agent-readiness gap reports.

Primary users:

- maintainers of agent-developed repositories
- engineering leads evaluating repository readiness

## Outcomes and success measures

Desired outcomes:

- Evidence-backed repository readiness and gap assessment
- A repeatable basis for prioritizing engineering-harness improvements

Success measures:

- Audit this template and one existing repository end to end
- Produce deterministic JSON and Markdown for an unchanged repository state
- Make no writes to the audited repository
- make smoke passes locally and in CI

## Scope

### In

- Local repository evidence collection
- Deterministic JSON and Markdown reports
- Harness and governance checks
- Git hygiene and CI checks
- Security-configuration and testing checks
- Agent-readiness checks
- Optional read-only GitHub metadata

### Out

- Automatic remediation
- Writes to audited repositories or GitHub
- Model calls or model-scored findings
- Full application behavior, architecture, data-flow, or runtime assessment
- Organization-wide aggregation

## Constraints

- Security: No secrets in the repository
- Data classification: potentially confidential source metadata and generated reports; local-only processing by default
- Deployment: local CLI; CI execution may be added only through a later accepted loop
- Budget: TBD
- Licensing: MIT

## Engineering and release contract

- Primary check: make smoke
- Dependency lock: uv.lock
- Coverage policy: branch-coverage-baseline-required-before-release
- Product versioning: semver at 0.1.0
- Version source: harness/project.yaml:engineering.versioning.current
- Public contract: CLI arguments and exit statuses, configuration schema, JSON report schema
- Harness version: 0.4.0

## Authority

- Autonomy level: supervised
- Network writes: explicit-human-approval
- Destructive actions: explicit-human-approval
- Release: human-only
- Policy changes: human-review

Generated from `harness/project.yaml` and `harness/intake.json`.
