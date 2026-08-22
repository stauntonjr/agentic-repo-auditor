# ADR-0006: Deterministic repository audit finding model

- Status: accepted
- Date: 2026-08-22
- Deciders: human owner (accepted 2026-08-22); independent verifier reviews implementation evidence
- Governing issue: LOCAL-1

## Context

Agentic Repo Auditor needs a public JSON contract that can represent repository-governance evidence without claiming to understand the complete application or reproduce specialized security scanners. The accepted v0.1 boundary is read-only, local-first, deterministic, and model-free. Inputs and reports may contain confidential repository metadata.

Observed primary-source evidence is recorded in [the repository auditor landscape](../research/repository-auditor-landscape.md). OpenSSF Scorecard and OSPS Baseline already define security checks and control vocabulary. GitHub exposes useful but time-varying authenticated metadata. SARIF defines a comprehensive static-analysis interchange model with stable fingerprints and provenance. AGENTS.md and Agent Skills define portable repository instruction and skill-discovery conventions.

The current unknown is whether downstream users will require SARIF or organization-wide aggregation. Neither is needed to prove the first local CLI boundary.

## Decision

Use a small product-owned report schema for v0.1 with:

- a versioned report and tool identity;
- a deterministic target state derived from repository name, commit, branch, index state, and content fingerprints for dirty, untracked, symlink, hidden-index, and nested-repository entries;
- stable finding IDs;
- explicit category, status, severity, title, description, evidence, and remediation;
- deterministic finding and evidence ordering;
- summary counts without an aggregate numeric readiness score; and
- JSON as the canonical machine representation with Markdown as a deterministic rendering.

The offline core may read content evidence only from non-symlink regular files inside the requested worktree. Git may read the repository's own metadata, including external worktree metadata, but is invoked with optional locks, repository-configured filesystem monitors and hooks, discovered clean/smudge/process filter drivers, and lazy fetching disabled. Filter discovery covers effective repository/worktree configuration and registered submodules before status inspection. The core must not require credentials, model calls, or network access. Its sole runtime dependency is pinned PyYAML 6.0.2 for semantic YAML parsing. GitHub, OpenSSF, SARIF, and other integrations remain adapters or exporters outside the core.

Workflow references are extracted from PyYAML's safe composed node graph, so block, flow, quoted, explicit-key, alias, merge, and multiline scalar forms share YAML semantics. Extraction is schema-located to reusable jobs at `jobs.<id>.uses` and action steps at `jobs.<id>.steps[*].uses`; unrelated `env`, `with`, and other mappings are not dependencies. The collector validates the node graph without constructing repository-controlled Python objects; ambiguous non-string Action references fail closed. Repository reads are capped at 2 MiB, with explicit node-count and nesting-depth limits.

Skill frontmatter uses PyYAML's safe loader after CRLF normalization. Required `name` and `description` values must be top-level strings; the name must equal its parent directory and satisfy the pinned Agent Skills syntax and length limits.

The first categories are governance, Git, CI, security, testing, and agent readiness. A check may report `pass`, `warn`, `fail`, `not-applicable`, or `unknown`. Live settings that cannot be observed locally must not be inferred from repository files.

Full application behavior, architecture, data-flow, and runtime assessment is intentionally a separate companion-product boundary.

## Consequences

### Positive

- Offline reports are reproducible, auditable, and safe for private repositories.
- Stable IDs and evidence can support future baselines, suppressions, framework mappings, and alternate renderers.
- Specialized tools remain authoritative for their domains.
- The core is portable across Git hosting providers.

### Negative

- v0.1 JSON is not directly consumable as SARIF.
- Local evidence cannot prove GitHub rulesets, secret scanning, dependency graph, collaborator MFA, or other privileged settings.
- A custom schema creates a compatibility obligation before real downstream consumers are known.
- Shallow structural agent checks cannot establish instruction quality or runtime behavior.
- PyYAML adds one pinned runtime and supply-chain dependency.

### Risks and mitigations

- Risk: users treat findings as compliance claims. Mitigation: keep evidence explicit, avoid a numeric score, and label unavailable evidence unknown or deferred.
- Risk: stable IDs change casually. Mitigation: treat IDs and JSON shape as SemVer-governed public contracts.
- Risk: checks duplicate OpenSSF behavior poorly. Mitigation: limit v0.1 to visible configuration signals and document external mappings rather than copied scoring.
- Risk: auditing executes repository-controlled helpers or changes the target. Mitigation: override fsmonitor, hooks, and discovered content filters; disable optional locks and lazy fetching; reject symlinked evidence; and test adversarial executable sentinels plus complete target snapshots before and after CLI runs.
- Risk: nested repository worktree content stays constant while its HEAD or index changes. Mitigation: bind nested and gitlink HEAD, staged index entries, assume-unchanged and skip-worktree flags, recursive gitlinks, and non-Git-metadata worktree content into the outer state ID.
- Risk: pathological YAML consumes excessive resources. Mitigation: cap evidence-file bytes, composed nodes, and nesting depth; use safe parsing only; and normalize parser failures into deterministic findings or exit-2 input errors.

## Alternatives considered

| Alternative | Evidence | Reason not selected |
|---|---|---|
| Use SARIF as the canonical schema | OASIS SARIF 2.1.0 Errata 01 supports findings, provenance, fingerprints, and baselines | Too broad for governance evidence; defer an exporter until a consumer requires it |
| Wrap OpenSSF Scorecard | Scorecard is mature and emits JSON | Security-only, network/provider-oriented, and does not cover the accepted harness and agent-readiness boundary |
| Query GitHub as the primary collector | GitHub APIs expose community, security, and dependency metadata | Violates offline determinism and adds credential/provider coupling |
| Produce one numeric readiness score | Common dashboard pattern | Hides uncertainty and encourages false comparison across unlike repositories |
| Include full application assessment | User identified the value of a comprehensive application report | Open-ended semantic/runtime scope would prevent a small deterministic first release |

## Verification and revisit trigger

Verify byte-identical JSON and Markdown on repeated runs, target-tree identity before and after, schema shape, stable ordering, failure exit behavior, mutable Action detection, clean wheel installation, and live audits of two different repositories.

Revisit when a real consumer requires SARIF, framework compliance, authenticated GitHub evidence, cross-run baselines, organization aggregation, or full-application analysis.
