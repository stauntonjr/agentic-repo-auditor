# Repository auditor landscape

- Decision: define the v0.1 audit boundary and finding/evidence model without duplicating established scanners.
- Search date: 2026-08-22.
- Scope: local repository governance, Git, CI, security configuration, testing, and agent-readiness evidence.
- Constraints: read-only by default, deterministic output, no model calls, no runtime dependency, potentially confidential local inputs, and portable JSON/Markdown reports.
- Stop condition: enough primary evidence to choose build, adopt, adapt, and defer boundaries for the first CLI slice.

## Source selection and queries

Primary sources were preferred: standards bodies, official product documentation, and canonical repositories. Repository popularity was treated only as a discovery signal. The search included `repository security audit scorecard JSON`, `repository community profile API`, `SARIF result schema fingerprint`, `AGENTS.md specification`, and `Agent Skills specification`.

| Candidate | Revision/version inspected | License/provenance | Relevant capability | Fit for v0.1 |
|---|---|---|---|---|
| [OpenSSF Scorecard](https://github.com/ossf/scorecard) | `d1fab88f54636ff366076edfc5c239f97b3c8e66` | Apache-2.0, canonical OpenSSF repository | Mature security-health checks and JSON output | Adapt category mappings later; do not reimplement or invoke in core |
| [OSPS Baseline](https://baseline.openssf.org/versions/2026-02-19.html) | 2026.02.19; source `e22b2db1843b8ab463742df1f1281cb7b4c5cfbf` | Apache-2.0, OpenSSF Security Baseline SIG | Versioned maturity controls for repository security posture | Reference control IDs where a local observation genuinely maps; do not claim compliance |
| [GitHub repository REST API](https://docs.github.com/en/rest/repos/repos) | API documentation inspected 2026-08-22 | GitHub first-party documentation | Community profile, repository metadata, and live security settings | Defer to an optional read-only adapter because local-only core must not require credentials |
| [GitHub dependency graph API](https://docs.github.com/en/rest/dependency-graph) | Versioned REST documentation inspected 2026-08-22 | GitHub first-party documentation | SBOM and dependency-review evidence | Defer until the GitHub adapter; do not infer live settings from files |
| [SARIF 2.1.0 plus Errata 01](https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html) | OASIS standard, 2023-08-28; repository `ed71d4f62db866ce3698a08a5ec3f7f2e775545d` | OASIS standard and normative schemas | Rich static-analysis interchange, stable fingerprints, locations, baselines | Adapt stable IDs and evidence concepts; defer a conforming exporter |
| [AGENTS.md](https://agents.md/) | Canonical repository `d1ac7f063d20e70015ed6732664049ae4ba9d74e` | MIT | Portable repository instruction discovery | Adopt filename discovery; assess content signals without imposing one prose template |
| [Agent Skills specification](https://github.com/agentskills/agentskills/blob/main/docs/specification.mdx) | `69ef37e9424c0a7ea9dd2293b559e43ec8176379` | Apache-2.0 | `SKILL.md` structure and metadata constraints | Adapt a shallow structural check; defer full conformance to the reference validator |

Maintenance was current at inspection time for all five canonical repositories. Those facts can drift; revisions above pin what was reviewed.

## Evidence-backed findings

1. OpenSSF Scorecard already covers security-specific signals including pinned dependencies, security policy, token permissions, dangerous workflows, SAST, packaging, and vulnerabilities. Reimplementing its scoring system would create weak duplication.
2. OSPS Baseline is a versioned control framework, not a promise that every control is externally observable. Its FAQ explicitly distinguishes publicly observable evidence from privileged settings and self-attestation. A local auditor must label unavailable live settings `unknown` or defer them.
3. GitHub exposes useful live repository and dependency metadata, but those calls introduce provider coupling, credentials, rate limits, and time-varying results. They do not belong in the deterministic offline core.
4. SARIF is intentionally broad static-analysis interchange. Its result fingerprints and provenance concepts are useful, but adopting the full schema would impose locations, runs, rules, and analysis semantics that the v0.1 governance report does not yet need.
5. AGENTS.md and Agent Skills supply portable discovery conventions. Presence and structural checks are defensible; judging semantic quality requires project-specific evidence and should not be reduced to a universal numeric score.

## Options

### Build

Build a dependency-free local collector and a small versioned report schema. Use stable finding IDs, explicit status/severity, evidence records, target state identity, deterministic ordering, and separate renderers. This is the smallest option that satisfies the accepted product contract.

### Adopt

Adopt established filenames and specification identifiers as references: AGENTS.md, SKILL.md, OSPS control IDs, and GitHub metadata names. Adoption means interoperable vocabulary, not copied implementation.

### Adapt

Adapt SARIF's stable identity and provenance principles and OpenSSF's separation of observable checks from policy claims. Preserve check-level evidence instead of producing an opaque aggregate readiness score.

### Defer

- A SARIF exporter until consumers need GitHub code-scanning or static-analysis interchange.
- Running or ingesting OpenSSF Scorecard until a security-adapter boundary is accepted.
- Authenticated GitHub checks until an optional read-only adapter can label permissions and freshness.
- Full application behavior, architecture, data-flow, and runtime assessment to a companion product.
- Model-assisted semantic scoring and automatic remediation.

## Recommendation

Build the deterministic offline core and custom v1 report now. Keep collectors, finding model, and renderers separate so future adapters can add external evidence without changing core semantics. Do not assign a universal numeric grade. Map external framework identifiers only when evidence and version are explicit. Treat SARIF as an optional future export, not the canonical internal model.

Confidence is high for the v0.1 boundary and medium for future interoperability. The first spike must prove byte-identical output, no target-tree changes, clean-install CLI behavior, mutable Action detection, and useful results on both this template and a mature existing repository.
