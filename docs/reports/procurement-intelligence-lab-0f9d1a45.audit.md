# Repository audit report

- Tool: `agentic-repo-auditor 0.1.0`
- Report schema: `1.2`
- Target: `procurement-intelligence-lab`
- Revision: `0f9d1a45af078ebf969f9ced11fc2e93adb542d0`
- Branch: `DETACHED`
- Dirty worktree: `no`
- State identity: `sha256:0943870d181b201f67b3d4c1c136ba2781aae202ea56446cfc91ec96dc82870a`

## Summary

| Status | Count |
|---|---:|
| pass | 9 |
| warn | 4 |
| fail | 0 |
| not-applicable | 0 |
| unknown | 0 |

## Findings

### agent-readiness.instructions: Agent instruction coverage

- Category: `agent-readiness`
- Status: `warn`
- Severity: `medium`
- Description: Repository instructions expose core evidence, verification, and safety signals.
- Evidence:
  - `signal-set` at `AGENTS.md`: present=['source', 'test', 'verification']; missing=['safety']; matches=['source:authority', 'test:test', 'verification:validate']
- Remediation: Document source precedence, tests, verification boundaries, and safety constraints.

### agent-readiness.skills: Portable agent skills

- Category: `agent-readiness`
- Status: `pass`
- Severity: `info`
- Description: Repository skills use discoverable SKILL.md files with basic portable metadata.
- Evidence:
  - `path-count` at `.agents/skills`: 13
- Remediation: Use one skill directory per capability with valid name and description frontmatter.

### ci.immutable-actions: Immutable workflow dependencies

- Category: `ci`
- Status: `pass`
- Severity: `info`
- Description: External Actions and container actions use immutable references.
- Evidence:
  - `action-summary` at `.github/workflows`: references=27
- Remediation: Pin third-party Actions to full commit SHAs and containers to image digests.

### ci.workflows: Continuous integration workflows

- Category: `ci`
- Status: `pass`
- Severity: `info`
- Description: At least one repository CI workflow is present.
- Evidence:
  - `path-count` at `.github/workflows`: 6
- Remediation: Add CI that runs the same authoritative check used locally.

### git.clean-worktree: Worktree state

- Category: `git`
- Status: `pass`
- Severity: `info`
- Description: The audit records whether the target has uncommitted or untracked state.
- Evidence:
  - `git-status` at `.`: changed_entries=0
- Remediation: Review and intentionally preserve, commit, or ignore outstanding worktree entries.

### governance.community-files: Community health files

- Category: `governance`
- Status: `warn`
- Severity: `low`
- Description: Basic purpose, contribution, and licensing files are present.
- Evidence:
  - `path-set` at `.`: present=['README.md', 'LICENSE']; missing=['CONTRIBUTING.md']
- Remediation: Add the missing community health files and keep them aligned with actual behavior.

### governance.instructions: Repository instructions

- Category: `governance`
- Status: `pass`
- Severity: `info`
- Description: Repository-level agent and contributor instructions are discoverable.
- Evidence:
  - `path-presence` at `.`: AGENTS.md
- Remediation: Add a root AGENTS.md with commands, boundaries, sources of truth, and safety rules.

### governance.project-contract: Machine-readable project contract

- Category: `governance`
- Status: `warn`
- Severity: `medium`
- Description: No recognized project intent and authority contract or explicit disposition is present.
- Evidence:
  - `project-contract` at `harness/project.yaml`: not available (absent)
- Remediation: Add harness/project.yaml or configure a safe repository-relative contract path or explicit not-applicable reason.

### security.code-scanning: Code scanning

- Category: `security`
- Status: `pass`
- Severity: `info`
- Description: The repository declares a CodeQL workflow as a visible code-scanning signal.
- Evidence:
  - `workflow-set` at `.github/workflows`: .github/workflows/codeql.yml
- Remediation: Configure code scanning appropriate to the repository languages and threat model.

### security.dependency-updates: Automated dependency updates

- Category: `security`
- Status: `pass`
- Severity: `info`
- Description: A recognized dependency-update configuration is present.
- Evidence:
  - `path-presence` at `.`: .github/dependabot.yml
- Remediation: Configure a reviewed dependency-update tool for every supported ecosystem.

### security.policy: Security policy

- Category: `security`
- Status: `warn`
- Severity: `medium`
- Description: A vulnerability-reporting policy is discoverable.
- Evidence:
  - `path-presence` at `.`: none found
- Remediation: Add SECURITY.md with supported versions and a private reporting channel.

### testing.primary-check: Authoritative local and CI check

- Category: `testing`
- Status: `pass`
- Severity: `info`
- Description: A machine-readable primary verification command is declared.
- Evidence:
  - `configured-primary-check` at `Makefile`: make check
- Remediation: Declare one authoritative command and run it unchanged in local and CI boundaries.

### testing.suite: Automated tests

- Category: `testing`
- Status: `pass`
- Severity: `info`
- Description: A conventional automated test suite is present.
- Evidence:
  - `path-count` at `tests`: 42
- Remediation: Add deterministic tests for the project's public and failure-path behavior.

## Configuration

Disabled checks: none.
Project-contract evidence: automatic detection.
Primary-check evidence: `make check` from `Makefile`.
