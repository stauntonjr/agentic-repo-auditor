# Changelog

All notable product changes are recorded here. Product and harness versions are independent.

## [0.1.0] - Unreleased

### Added

- Read-only local repository audit CLI with deterministic JSON and Markdown output.
- Versioned configuration and report schemas.
- Governance, Git, CI, security, testing, and agent-readiness checks.
- Clean-install package and CLI verification.
- Portable project-contract evidence through a safe repository-relative JSON or YAML path, or an
  explicit bounded not-applicable disposition.
- Portable primary-check evidence through an exact command and safe repository-relative provenance
  source, or an explicit bounded not-applicable disposition.

### Changed

- Reconciled the generated template identity with Agentic Repo Auditor.
- Hardened Git collection against repository-configured fsmonitor, hook, and content-filter execution plus lazy fetching.
- Bound target state IDs to dirty index/worktree content, symlinks, hidden-index entries, and nested repository HEAD/staged-entry/hidden-flag/worktree state.
- Added conservative YAML-aware workflow reference extraction and repository-contained file reads.
- Replaced the provisional YAML subset with bounded PyYAML semantic parsing for workflows and Skill frontmatter.
- Scoped Action extraction to reusable-job and action-step schema locations, including aliases and merges.
- Enforced top-level Skill metadata, directory/name equality, specification length limits, and CRLF compatibility.
- Applied shared YAML node-count and nesting-depth limits before workflow or Skill interpretation.
- Replaced literal-substring agent-instruction checks with token-bounded, explainable vocabulary
  that recognizes equivalent authority, testing, safety, and verification terms.
- Advanced configuration and report schemas to 1.1 for normalized, deterministic evidence
  declarations while preserving schema 1.0 inputs without declarations.
- Advanced configuration and report schemas to 1.2 for primary-check declarations while preserving
  schema 1.0 and 1.1 inputs within their original capabilities.

## Harness baseline [0.4.0] - 2026-08-22

### Added

- Provider-neutral roles, skills, engineering loop, evidence reports, intake, GitHub planning, and project profiles.
- Codex and experimental Pi adapters.
- Integrity-checked write scopes, independent verifier verdicts, and provenance-locked harness upgrades.
- Configurable product-version, engineering-quality, and GitHub security contracts.
- Dependabot, dependency review, CodeQL, and immutable GitHub Actions validation.

### Security

- Completion fingerprints worktree, index, hidden index flags, submodules, and embedded repositories.
- Third-party GitHub Actions are pinned to reviewed full commit SHAs.
