# Project handoff

This is a concise orientation index for a fresh human or agent. It is not a transcript, decision log, or second roadmap.

## Read first

1. `AGENTS.md`.
2. `harness/project.yaml`.
3. The active GitHub Issue and Project item.
4. Linked files in `docs/adr/`.
5. The relevant repository-local skill.

## Current state

- Harness version: 0.4.0.
- Product version: 0.1.0, unreleased.
- Project status: active; greenfield intake accepted 2026-08-22.
- Active engineering loop: none after LOCAL-1 reconciliation.
- Release state: local candidate only; no release authorization or remote publication.
- Intended repository: `stauntonjr/agentic-repo-auditor`.

## Implemented product slice

- Read-only local Git repository audit CLI.
- Deterministic JSON and Markdown rendering from one finding/evidence model.
- Versioned configuration and report schemas.
- Stable finding IDs, explicit status and severity, evidence, remediation, and target state identity.
- Governance, Git, CI, security, testing, and agent-readiness checks.
- Configurable check suppression with fail-closed validation.
- CLI exit thresholds for advisory and gating use.
- Clean-install wheel and installed-entrypoint smoke boundary.
- Primary-source landscape research and proposed ADR-0006.

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

- Human acceptance or revision of proposed ADR-0006 before public release.
- Which existing repository should be the first published dogfood report target.
- Whether the intended GitHub repository should be public or private.
- Whether GitHub Project creation should copy a canonical user Project or render fields from desired state.
- When to add an authenticated, read-only GitHub evidence adapter.
- Whether downstream consumers require SARIF export or cross-run baselining.
- The separate product boundary and name for full-application assessment.

## Refresh protocol

Update this index only when current state, settled decisions, active work, or the recommended next loop changes materially. Link to authoritative evidence instead of duplicating it.
