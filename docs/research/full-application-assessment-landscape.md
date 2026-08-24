# Full-application assessment landscape

- Decision: define the boundary and first useful slice for a companion to Agentic Repo Auditor.
- Search date: 2026-08-24.
- Scope: application structure, behavior, data flow, runtime, domain meaning, quality attributes,
  and executive reporting.
- Constraints: separate repository; read-only target handling; local-only processing by default;
  evidence-backed claims; explicit unknowns; no repository bootstrap before human approval.
- Stop condition: enough primary evidence to select build, adopt, adapt, and defer boundaries and
  identify the remaining project-intake decisions.

## Research method

Primary standards, official documentation, and canonical repositories were preferred. Product
marketing and popularity were not treated as proof of coverage or quality. Repository revisions
pin the implementation and license metadata inspected on the search date; documentation without a
repository revision is identified by its published version or inspection date.

Searches covered `application architecture assessment`, `code property graph`, `static data flow`,
`runtime architecture trace`, `architecture documentation`, `architecture tradeoff analysis`,
`automated code review`, and the interchange formats used by those tool families.

## Candidate evidence families

| Candidate | Revision or version inspected | License or provenance | Useful evidence | Boundary and disposition |
|---|---|---|---|---|
| [arc42](https://arc42.org/overview/) | Template 9.0; canonical template `8dff0d9b1f9640684df8c3bbcdc2ee45f989ca0f` | Official site says free, open source, and usable commercially; individual assets retain their declared terms | A coherent report outline spanning goals, constraints, context, building blocks, runtime, deployment, decisions, quality, risks, and glossary | **Adapt** the coverage checklist, not its prose; every section must still distinguish observed, declared, derived, and unavailable evidence |
| [C4 model](https://c4model.com/) | Official site inspected 2026-08-24 | Official examples are CC BY 4.0; the method is notation- and tooling-independent | Consistent system, container, component, dynamic, and deployment abstractions | **Adapt** vocabulary and view levels; a folder or package is not automatically a C4 component, so generated mappings remain hypotheses until confirmed |
| [Structurizr](https://docs.structurizr.com/dsl) | `structurizr/structurizr@9ff16634c3b8574584262ae8545510bbb1d1b4bd` | Apache-2.0 | Text model plus views; exports to JSON, PlantUML, Mermaid, and static HTML | **Defer** as an optional exporter. Do not make a Java DSL runtime or diagram layout part of the first evidence core |
| [ATAM](https://www.sei.cmu.edu/library/the-architecture-tradeoff-analysis-method/) | CMU/SEI-98-TR-008 | Primary SEI method/report | Stakeholder scenarios and tradeoffs among modifiability, security, performance, availability, and other qualities | **Adapt** the scenario discipline. Automated inspection cannot decide architectural fitness without the decisions and quality attributes that matter to the user |
| [ISO/IEC 25010:2023](https://www.iso.org/standard/78176.html) | Edition 2, 2023-11 | International standard; normative text is not bundled | Product-quality vocabulary and evaluation framing | **Reference**, without claiming conformance or copying the paid standard. Select measurable qualities during intake instead of issuing a universal score |
| [GitHub CodeQL](https://docs.github.com/en/code-security/concepts/code-scanning/codeql/codeql-code-scanning) | `github/codeql@f2ce282ecec7d481dab4458e577922a46a741db2` | Query repository MIT; CLI and use remain subject to GitHub's CodeQL terms | Language-aware databases, queries, security/error findings, data flow, SARIF | **Adapt** SARIF as an optional input. Database creation can invoke builds and has language, licensing, resource, and trust boundaries, so it is not a silent core step |
| [Joern](https://docs.joern.io/) | `joernio/joern@66877d6518fe1da39e621acf16c268d508a6b8b6` | Apache-2.0 | Cross-language code property graphs combining syntax, control flow, and data flow | **Evaluate later** as an advanced static adapter. It is a substantial JVM/Scala toolchain and a program graph does not establish runtime coverage or domain intent |
| [SCIP](https://sourcegraph.com/docs/code-navigation/precise-code-navigation) | `scip-code/scip@02559b6181bcf7a53e93c80995a798457117c431` | Apache-2.0 | Language-neutral symbol definitions, references, and implementations from compiler-aware indexers | **Evaluate later** as a code-navigation import. Indexer availability and build requirements vary by language |
| [Semgrep](https://semgrep.dev/docs/) | `semgrep/semgrep@a0c13f304151e531c7e7c00838076211a07a790c` | OSS engine LGPL-2.1; Semgrep-maintained rules and hosted features have separate terms | Pattern and data-flow findings across many languages; SARIF-capable analysis | **Adapt** supported result files only after provenance validation. Do not bundle rules or assume hosted-product rights from the engine license |
| [SonarQube Server](https://docs.sonarsource.com/sonarqube-server/analyzing-source-code/analysis-overview) | `SonarSource/sonarqube@506532b9f249afdb3d6f5840e8a679b633ba2265` | Community source LGPL-3.0; advanced and architecture capabilities vary by commercial edition | Automated code-review findings and metrics for reliability, security, maintainability, coverage, complexity, and duplication | **Integrate by import, not reimplementation**, if a user already has results. Metrics are tool-defined observations, not a complete application assessment |
| [AppMap data](https://github.com/getappmap/appmap) | `getappmap/appmap@fa68b137cca857824684ccd2ac2cece38fd622d9` | Canonical specification repository did not contain a license file at inspection | Runtime call events, code objects, HTTP, SQL, and other behavior used for dependency and sequence views | **Defer** direct adoption until licensing is explicit. Consider sanitized, user-supplied trace import later; recordings may contain parameters, return values, headers, SQL, and confidential topology |
| [OpenTelemetry](https://opentelemetry.io/docs/concepts/observability-primer/) | Specification 1.60.0; `open-telemetry/opentelemetry-specification@1377f53b2bc0683c45169b8f20fd973eb4d59419` | Apache-2.0 | Traces, metrics, logs, resource identity, and semantic conventions for observed runtime behavior | **Adapt** OTLP/semantic-convention imports later. Instrumentation and collection are external effects and only cover exercised behavior |
| [SARIF 2.1.0 with Errata 01](https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html) | OASIS standard, 2023-08-28 | OASIS standard and normative schemas | Static-analysis runs, rules, locations, provenance, fingerprints, and baselines | **Adopt as an optional interchange input**, while retaining the companion's broader evidence model for non-finding observations and human assertions |
| [CycloneDX 1.7](https://cyclonedx.org/specification/overview/) and [SPDX 3](https://spdx.dev/use/specifications/) | CycloneDX 1.7; SPDX 3.0 current at inspection | OWASP/Ecma and ISO/IEC 5962 standards | Components, services, dependencies, relationships, licenses, and supply-chain metadata | **Adopt as optional inventory inputs** rather than inventing another SBOM parser or vulnerability database |

Maintenance and product terms can drift. A future implementation loop must repin and recheck each
dependency or adapter before adoption.

## Evidence-backed findings

1. **There is no honest single-source full-application analyzer.** Static analyzers observe only
   supported languages and modeled constructs. Runtime tools observe only executed paths and
   environments. Architecture methods require stakeholder goals and scenarios. Domain semantics
   require authoritative human or project declarations.
2. **Static structure is not architecture by itself.** C4 explicitly separates software systems,
   deployable containers, components, and code. arc42 adds goals, constraints, runtime,
   deployment, decisions, and risks. Package and call graphs can support those views but cannot
   name responsibilities or quality tradeoffs on their own.
3. **Execution is a separate trust tier.** CodeQL database creation, compiler-aware SCIP indexers,
   dependency resolution, tests, instrumented runs, and telemetry collection may execute target or
   dependency code, access networks, or expose secrets. A tool that does these implicitly cannot
   preserve the Auditor's read-only local safety boundary.
4. **Architecture fitness is decision-relative.** ATAM evaluates competing quality attributes
   through scenarios; ISO/IEC 25010 supplies a quality vocabulary, not a project-specific answer.
   A universal numeric architecture score would hide both stakeholder priorities and missing
   evidence.
5. **Existing interchange formats should remain authoritative in their domains.** SARIF is suited
   to static findings, CycloneDX/SPDX to software inventories, and OpenTelemetry to runtime
   signals. The companion needs an evidence envelope that references these artifacts rather than
   flattening them into lossy prose.
6. **A useful executive report needs epistemic labels.** At minimum, every claim must be one of:
   directly observed, imported tool result, human-declared, deterministically derived, model-
   synthesized, or unavailable. A citation must bind it to an exact target and source artifact.

## Options

### Extend Agentic Repo Auditor

Rejected. The Auditor's accepted contract is a deterministic, model-free repository-readiness
check. Adding application semantics, runtime execution, or model synthesis would weaken its safety
and public-contract clarity.

### Adopt one analysis platform

Deferred. CodeQL, Joern, Semgrep, SonarQube, AppMap, and OpenTelemetry each cover valuable but
different evidence and trust boundaries. Selecting one as the product core would make unsupported
languages, licensing, hosted services, or runtime instrumentation define the product.

### Generate a report directly with an agent

Rejected as the canonical core. It is useful for synthesis, but without a versioned evidence model
it cannot provide reproducible coverage, stable identity, precise citations, or a defensible
distinction between fact and interpretation.

### Build a separate evidence compiler with adapters

Recommended. Build a small local core that inventories inspectable application evidence, imports
versioned external artifacts, records human assertions and unknowns, and produces canonical JSON
plus deterministic Markdown. Keep optional model-assisted narrative and executable collectors as
separate, explicitly authorized adapters.

## Recommended product boundary

The companion should answer: **What can we establish about this application's purpose, structure,
interfaces, data movement, runtime shape, quality risks, and important unknowns from the evidence
the user authorized?** It should not claim that unexecuted paths are correct, that generated
diagrams are the intended architecture, or that an application is compliant, secure, or
production-ready.

The provisional first slice is:

1. Read an exact local Git worktree without writing to it.
2. Accept a user-reviewed context file containing purpose, stakeholders, key workflows, data
   classifications, quality scenarios, and declared component responsibilities.
3. Accept an optional Agentic Repo Auditor JSON report for the same target state.
4. Collect bounded static evidence from manifests, source layout, entrypoints, schemas, interfaces,
   deployment/configuration files, tests, documentation, and ADRs without executing target code.
5. Emit a canonical evidence graph and deterministic Markdown assessment with source locations,
   contradictions, coverage limits, and unknowns.
6. Produce system-context and container-level *proposals* only where evidence is sufficient; mark
   every inferred element and relationship for confirmation.

The first slice excludes target execution, dependency installation, network access, credentials,
live production telemetry, vulnerability-database claims, automatic remediation, model-scored
quality, and organization-wide aggregation.

## Provisional exchange contract with Agentic Repo Auditor

The products remain independently runnable and versioned.

- Input is the Auditor's canonical JSON file, never scraped Markdown.
- The companion records the input file SHA-256, Auditor tool version, report schema version, target
  state ID, target revision, and its own import provenance. The current Auditor schema does not
  claim to preserve the original CLI invocation.
- The companion accepts the report only when the target repository identity and state match its own
  assessment target. Mismatch is a deterministic input error; absence remains supported and is
  reported as unavailable repository-readiness evidence.
- Auditor findings retain their original IDs, statuses, severities, descriptions, evidence, and
  remediation under a `repo-readiness` source namespace. The companion does not recompute or
  reinterpret their pass/fail state.
- Application evidence uses separate stable IDs and claim types. A relationship between an
  application observation and an Auditor finding is an explicit reference, not a copied finding.
- The companion report links to the exact Auditor artifact and includes its digest. It never writes
  back to the Auditor report, target repository, or GitHub.
- Schema compatibility is adapter-owned. An unsupported Auditor schema fails with a precise error;
  it does not silently drop fields.

The companion's own canonical envelope should be product-owned because it must represent more than
findings: evidence artifacts, human assertions, components, interfaces, relationships, scenarios,
claims, contradictions, and unknowns. Where an established interchange exists, the envelope should
reference the original artifact and preserve its version rather than duplicate the whole standard.

## Recommendation and confidence

Proceed with a separate MIT-eligible Python CLI repository only after the human owner confirms its
name, license, profile, publication policy, first audience/decision, first dogfood target, and
whether model-assisted synthesis belongs in v0.1. The recommended working name is
`agentic-application-assessor`; GitHub name searches for that exact phrase,
`application-evidence-lab`, and `full-application-assessor` returned no repositories on the search
date.

Confidence is high in the separate evidence-first boundary, high that executable/runtime analysis
must be an explicit later trust tier, and medium in the proposed first static slice until a user and
first target are selected.
