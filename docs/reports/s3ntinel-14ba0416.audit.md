# Repository audit report

- Tool: `agentic-repo-auditor 0.1.0`
- Report schema: `1.0`
- Target: `S3NTINEL`
- Revision: `14ba0416e06f6a9b57a8f7b02fdef1bb09a2f1cc`
- Branch: `DETACHED`
- Dirty worktree: `no`
- State identity: `sha256:6896104ea02c57f3a86cae918d10415e7f0d422a08c47ac129dbeefd8d842174`

## Summary

| Status | Count |
|---|---:|
| pass | 4 |
| warn | 8 |
| fail | 1 |
| not-applicable | 0 |
| unknown | 0 |

## Findings

### agent-readiness.instructions: Agent instruction coverage

- Category: `agent-readiness`
- Status: `warn`
- Severity: `medium`
- Description: Repository instructions expose core evidence, verification, and safety signals.
- Evidence:
  - `signal-set` at `AGENTS.md`: present=['test', 'safety', 'verification']
- Remediation: Document source precedence, tests, verification boundaries, and safety constraints.

### agent-readiness.skills: Portable agent skills

- Category: `agent-readiness`
- Status: `warn`
- Severity: `low`
- Description: Repository skills use discoverable SKILL.md files with basic portable metadata.
- Evidence:
  - `path-count` at `.agents/skills`: 0
- Remediation: Use one skill directory per capability with valid name and description frontmatter.

### ci.immutable-actions: Immutable workflow dependencies

- Category: `ci`
- Status: `fail`
- Severity: `high`
- Description: External Actions and container actions use immutable references.
- Evidence:
  - `action-summary` at `.github/workflows`: references=2
  - `mutable-action` at `.github/workflows/ci.yml`: actions/checkout@v4
  - `mutable-action` at `.github/workflows/ci.yml`: actions/setup-python@v5
- Remediation: Pin third-party Actions to full commit SHAs and containers to image digests.

### ci.workflows: Continuous integration workflows

- Category: `ci`
- Status: `pass`
- Severity: `info`
- Description: At least one repository CI workflow is present.
- Evidence:
  - `path-count` at `.github/workflows`: 1
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
  - `path-set` at `.`: present=['README.md']; missing=['CONTRIBUTING.md', 'LICENSE']
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
- Description: A durable project intent and authority contract is present.
- Evidence:
  - `path-presence` at `.`: none found
- Remediation: Add a machine-readable project contract or document why one is not used.

### security.code-scanning: Code scanning

- Category: `security`
- Status: `warn`
- Severity: `medium`
- Description: The repository declares a CodeQL workflow as a visible code-scanning signal.
- Evidence:
  - `workflow-set` at `.github/workflows`: none found
- Remediation: Configure code scanning appropriate to the repository languages and threat model.

### security.dependency-updates: Automated dependency updates

- Category: `security`
- Status: `warn`
- Severity: `medium`
- Description: A recognized dependency-update configuration is present.
- Evidence:
  - `path-presence` at `.`: none found
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
- Status: `warn`
- Severity: `medium`
- Description: A machine-readable primary verification command is declared.
- Evidence:
  - `project-contract` at `harness/project.yaml`: not declared
- Remediation: Declare one authoritative command and run it unchanged in local and CI boundaries.

### testing.suite: Automated tests

- Category: `testing`
- Status: `pass`
- Severity: `info`
- Description: A conventional automated test suite is present.
- Evidence:
  - `path-count` at `tests`: 79
- Remediation: Add deterministic tests for the project's public and failure-path behavior.

## Configuration

Disabled checks: none.
