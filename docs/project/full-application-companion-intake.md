# Full-application companion intake decision packet

- Governing issue: [#11](https://github.com/stauntonjr/agentic-repo-auditor/issues/11).
- Intake mode: `new`, pre-bootstrap discovery.
- Status: provisional; material human decisions remain open.
- Last reconciled: 2026-08-24.
- Boundary: this record does not create, name, publish, or license a companion repository.

## Why this exists

Agentic Repo Auditor establishes repository engineering and agent-readiness evidence. It explicitly
does not assess full application behavior, architecture, data flow, runtime, or domain semantics.
The desired companion would produce a comprehensive, evidence-backed application report without
weakening that boundary.

The [landscape research](../research/full-application-assessment-landscape.md) supports a separate,
evidence-first product. It does not resolve which decisions the first report must support, which
application should prove the design, or how much execution and model synthesis the user wants.

## Reconciled context

| Intake topic | Current value | Status | Source |
|---|---|---|---|
| Product need | A comprehensive report covering application purpose, architecture, data flow, runtime, domain semantics, quality risks, and unknowns | confirmed | Human request and Issue #11 |
| Relationship to Auditor | Separate companion product; consume an exact Auditor JSON artifact without duplicating its checks | confirmed boundary, proposed contract | ADR-0006, Issue #11, landscape research |
| Likely users | Repository maintainers and engineering leads assessing an unfamiliar or agent-developed application | provisional | Auditor users plus stated reporting need |
| Primary decision | Understand the system and prioritize investigation or engineering work | provisional | Inferred from the requested executive report |
| Processing default | Local-only, read-only target inspection | provisional recommendation | Auditor safety boundary and research |
| Data classification | Potentially confidential source, architecture, domain descriptions, runtime topology, and generated reports | provisional recommendation | Auditor contract plus runtime-tool evidence |
| First implementation profile | Python CLI/data product with agent-system concerns treated as an additional evaluation boundary | provisional recommendation | Existing profiles and likely artifact pipeline |
| License | Not selected; MIT is recommended for consistency and broad reuse | TBD | Human approval required by Issue #11 |
| Visibility | Not selected; no repository exists | TBD | Human approval required by Issue #11 |
| Product name | `agentic-application-assessor` is the recommended working name | TBD | Collision search and product relationship |

## Proposed users and decisions

The smallest coherent audience is an engineering lead or maintainer who needs to answer:

- What does this application appear to do, and which claims are declared versus observed?
- What are its major deployable units, responsibilities, interfaces, data stores, and external
  dependencies?
- Which important workflows have static or runtime evidence, and which remain unobserved?
- Which architecture decisions and quality scenarios drive the design?
- Where do evidence sources contradict each other?
- What are the highest-value investigation or engineering follow-ups?

The first product should not target compliance certification, automated security approval,
production readiness, model-quality evaluation, or autonomous remediation.

## Proposed data and trust tiers

| Tier | Inputs | Default in v0.1 | Trust and safety boundary |
|---|---|---|---|
| 0: target identity | Local Git metadata and bounded file fingerprints | yes | No target writes; hostile Git helpers and symlink escapes must be neutralized or rejected |
| 1: static repository evidence | Source, manifests, schemas, docs, ADRs, tests, deployment/configuration files | yes | Bounded regular-file reads; no imports, builds, dependency resolution, or target execution |
| 2: declared context | User-reviewed purpose, stakeholders, component responsibilities, workflows, data classifications, and quality scenarios | yes | Assertions remain visibly declared and dated; contradictions are preserved |
| 3: imported analysis | Auditor JSON, SARIF, SPDX/CycloneDX, SCIP, coverage, and test artifacts | Auditor JSON only at first | Validate schema, provenance, exact target, and digest; retain original tool identity and terms |
| 4: executable analysis | Builds, tests, CodeQL databases, compiler indexers, dependency resolution, instrumentation | no | Requires explicit authorization, isolation, resource limits, and separate output provenance |
| 5: live runtime evidence | Sanitized traces, metrics, logs, and deployment state | no | May contain secrets, personal data, payloads, and infrastructure topology; separate credentials and retention policy |
| 6: model synthesis | Narrative, proposed responsibilities, inferred relationships, and prioritized questions | undecided | Must cite evidence, label inference, record model/prompt identity, and never overwrite canonical observations |

## Proposed success metrics

These are recommendations pending human confirmation:

1. Repeated assessment of an unchanged target and unchanged inputs produces byte-identical
   canonical JSON and deterministic Markdown.
2. Every report claim has an exact source, origin class, target identity, and derivation status, or
   is explicitly unavailable.
3. The assessment changes no target file, Git metadata, network state, or external service.
4. A maintainer can confirm or reject proposed system/container responsibilities without editing
   generated evidence by hand.
5. The first dogfood report identifies at least one material contradiction or unknown and leads to
   a concrete, human-accepted follow-up decision.
6. Unsupported languages, schemas, and missing context degrade to explicit coverage gaps rather
   than false-green conclusions.

## Proposed first vertical slice

Build a Python CLI that takes an exact local repository plus a small, user-reviewed context file
and optional matching Agentic Repo Auditor JSON. It produces:

- a versioned canonical evidence graph;
- a deterministic executive Markdown report;
- static inventory of manifests, entrypoints, interfaces, schemas, data stores, deploy/runtime
  declarations, tests, architecture docs, and ADRs;
- proposed system-context and container-level views with every inferred element labeled;
- contradictions, coverage limits, and open questions; and
- a content-bound reference to any imported Auditor report.

The slice does not execute the target, install dependencies, contact GitHub, collect live telemetry,
or call a model. A later optional synthesis adapter may turn the canonical evidence into richer
narrative after its evaluation and privacy contract is accepted.

## Decisions required before bootstrap

### D1. First audience and decision

Recommended: an engineering lead or maintainer onboarding to an unfamiliar application and deciding
what to investigate or improve next.

Alternatives include architecture review, acquisition/due diligence, incident reconstruction, or
release readiness. Choosing one changes the evidence priorities and acceptance tests.

### D2. First dogfood application

Recommended: Agentic Repo Auditor itself for the zero-execution contract, followed by Macro
Technical Pulse for domain/data-flow depth. Starting directly with Macro Technical Pulse would
provide richer semantics but increases the first-slice scope and confidentiality review.

### D3. Model boundary

Recommended: deterministic evidence and Markdown in v0.1; model-assisted synthesis as an optional,
versioned adapter after the core is independently verified.

Alternative: include a local-model narrative in v0.1. That requires model/prompt provenance,
repeatability expectations, evaluation fixtures, cost/latency limits, and explicit rules for
confidential inputs.

### D4. Identity and publication

Recommended proposal:

- repository/name: `stauntonjr/agentic-application-assessor`;
- license: MIT;
- visibility: public source after local acceptance and secret/history scanning;
- profile: `python-data`, with agent-system evaluation requirements recorded explicitly;
- versioning: SemVer starting at `0.1.0` unreleased; and
- no tag, GitHub Release, package publication, or live deployment without separate authorization.

No exact-name collision was found on GitHub on 2026-08-24. The human owner must still approve every
item above before creation or publication.

### D5. Runtime roadmap

Recommended: accept only sanitized, pre-recorded runtime artifacts in the next trust tier. Do not
instrument or launch arbitrary target applications until an isolation, secret-handling, retention,
and resource policy is accepted and tested.

## Context-readiness decision

There is enough evidence to recommend a product boundary and ask a focused decision set. There is
not enough human intent or authority to render an active project contract or create the repository.
Bootstrap remains blocked on D1-D4. D5 may remain provisional if runtime collection is explicitly
out of v0.1.

Once those choices are confirmed, run `project-intake` in `new` mode in the new repository, record
the accepted answers with source and date, render the selected profile, create the architecture ADR,
and implement only the first read-only vertical slice.
