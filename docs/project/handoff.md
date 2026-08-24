# Project handoff

This is a concise orientation index for a fresh human or agent. It is not a transcript, decision log, or second roadmap.

## Read first

1. `AGENTS.md`.
2. `harness/project.yaml`.
3. The active GitHub Issue and Project item.
4. Linked files in `docs/adr/`.
5. The relevant repository-local skill.

## Current state

- Harness version: 0.4.1.
- Product version: 0.1.0, unreleased.
- Project status: active; greenfield intake accepted 2026-08-22.
- Completed product loop: `20260822T164511Z-33525376`, revision 4 attempt 1 for LOCAL-1, reported at content-equivalent rewritten commit `7de7119` after independent AC1-AC5 approval.
- Architecture: ADR-0006 accepted on 2026-08-22; ADR-0007 portable evidence declarations accepted
  by the human owner on 2026-08-24; ADR-0008 portable primary-check declarations accepted on
  2026-08-24.
- Publication state: public source is available at `stauntonjr/agentic-repo-auditor`; no tag, GitHub Release, or package-registry publication is authorized.
- Product release state: version 0.1.0 remains unreleased.
- First existing-repository dogfood: Issue #8 audits public S3NTINEL commit `14ba0416e06f6a9b57a8f7b02fdef1bb09a2f1cc`; canonical JSON, Markdown, and triage live under `docs/reports/`.
- Issue #13 repairs the dogfood's false instruction-coverage warning with a deterministic,
  token-bounded vocabulary and exact matched-term evidence; it does not claim semantic prose
  understanding.
- Issue #12 adds schema-1.1 portable project-contract evidence: a safe repository-relative JSON or
  YAML object or an explicit bounded not-applicable reason. Automatic `harness/project.yaml`
  compatibility remains.
- Issue #14 adds schema-1.2 portable primary-check evidence: an exact non-executed command with a
  safe repository-relative provenance source, or an explicit bounded not-applicable reason.

## Implemented product slice

- Read-only local Git repository audit CLI.
- Deterministic JSON and Markdown rendering from one finding/evidence model.
- Versioned configuration and report schemas, including normalized portable evidence declarations.
- Stable finding IDs, explicit status and severity, evidence, remediation, and target state identity.
- Governance, Git, CI, security, testing, and agent-readiness checks.
- Configurable check suppression with fail-closed validation.
- Bounded semantic YAML parsing for workflows and Skill metadata through pinned PyYAML 6.0.2.
- CLI exit thresholds for advisory and gating use.
- Clean-install wheel and installed-entrypoint smoke boundary.
- Primary-source landscape research and accepted ADR-0006.

## Implemented control plane

- Machine-readable project, role, loop, schema, profile, and planning contracts.
- Repository-local skills for intake, existing-solution research, execution, reporting, GitHub planning, ADRs, and release readiness.
- Codex role adapters with separated planner, explorer, implementer, verifier, and release-steward authority.
- Experimental Pi adapter with native skill discovery, workflow prompts, ignored session state, structured context questions, and explicit delegation/sandbox limitations.
- Dependency-free validators, intake rendering, loop evidence, reporting, and GitHub audit/dry-run tools.
- Criterion-linked completion gates with revision-bound verifier verdicts and content-aware baseline/write-scope enforcement.
- Provenance-locked, ownership-aware three-way upgrade plans with explicit apply resolutions, receipts, and rollback.
- Eight isolated forward-test scenarios covering routing, context gaps, evidence, and safety behavior.
- CI for the harness itself.
- Separate harness and product version contracts with current-revision release-impact reporting.
- Profile-driven quality capabilities, concrete Python defaults, repository hygiene files, and a shared local/CI command boundary.
- Dependabot, dependency review, CodeQL, least-privilege workflows, and deterministic full-SHA Action validation.

## Open decisions

- Whether GitHub Project creation should copy a canonical user Project or render fields from desired state.
- When to add an authenticated, read-only GitHub evidence adapter.
- Whether downstream consumers require SARIF export or cross-run baselining.
- The separate product boundary and name for full-application assessment.

## Recommended next loop

Audit a second existing repository with the portable evidence configuration, then use dogfood
results to decide authenticated GitHub evidence, SARIF, baselining, and the full-application
companion boundary.

## Refresh protocol

Update this index only when current state, settled decisions, active work, or the recommended next loop changes materially. Link to authoritative evidence instead of duplicating it.
