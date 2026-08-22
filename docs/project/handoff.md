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
- Project status: template; project intake not yet accepted.
- Active engineering loop: none.
- Release state: not applicable.
- Publication target: public GitHub template `stauntonjr/agentic-project-template`.

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

- Which repository should be the first live dogfood target.
- Whether GitHub Project creation should copy a canonical user Project or render fields from desired state.
- Which live repository should dogfood the Pi adapter's intake-to-report path.
- Which live GitHub security settings should be reconciled automatically after the first dogfood audit.

## Refresh protocol

Update this index only when current state, settled decisions, active work, or the recommended next loop changes materially. Link to authoritative evidence instead of duplicating it.
