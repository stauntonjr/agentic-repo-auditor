# ADR-0007: Portable configured evidence declarations

- Status: accepted
- Date: 2026-08-24
- Deciders: human owner (accepted 2026-08-24); independent verifier reviews implementation evidence
- Governing issues: #12 and #14

## Context

The first S3NTINEL dogfood audit showed that two general-purpose findings were coupled to
`harness/project.yaml`. The project-contract remediation also promised that a documented exception
could satisfy the finding even though no such evidence was implemented. The human owner approved a
portable configuration contract that preserves automatic harness compatibility, permits explicit
repository-relative evidence, and records bounded not-applicable dispositions with reasons.

The auditor is offline, deterministic, model-free, and read-only. Configuration therefore cannot
authorize arbitrary file traversal, symlink following, command execution, or inference from prose.
Its normalized declarations are part of the public JSON report contract.

## Decision

Configuration schema 1.1 adds an `evidence` object. Each supported evidence key has a closed,
check-specific schema and fail-closed runtime validation. Schema 1.0 configurations remain accepted
when they do not contain evidence declarations.

For `governance.project-contract`, `evidence.project_contract` accepts exactly one of:

- `path`: a normalized repository-relative `.json`, `.yaml`, or `.yml` path; or
- `not_applicable_reason`: a trimmed, non-empty, single-line reason of bounded length.

Configured paths must resolve through existing non-symlink components to a regular file inside the
audited repository. The file must be bounded UTF-8 and parse as a non-empty JSON or safe YAML object.
Missing, malformed, escaping, symlinked, or otherwise unsafe configured evidence terminates the
audit as invalid input. Without a declaration, the conventional `harness/project.yaml` path remains
automatic evidence; absence or malformed automatic evidence produces a warning rather than an input
error.

The canonical report schema advances to 1.1 and always emits the normalized project-contract
configuration, including `null` for automatic detection. Findings record the exact recognized path
or the exact disposition reason. Markdown renders the same normalized configuration.

Issue #14 may add a closed `primary_check` declaration under the same `evidence` object. Its command
and provenance validation remains scoped to that issue. Arbitrary README prose, CI presence, and
unregistered evidence keys are not authoritative.

## Consequences

### Positive

- General repositories can satisfy the finding without adopting the template path.
- Explicit exceptions are visible, deterministic, and reviewable rather than silent suppressions.
- Harness-derived repositories retain zero-configuration compatibility.
- Unsafe declarations fail before a report can misrepresent them as evidence.

### Negative

- Configuration and report schema consumers must understand schema 1.1 to use the new evidence
  shape.
- A declared path proves only a valid machine-readable object, not that its contents are truthful or
  complete.
- Not-applicable reasons remain human assertions; the auditor records but cannot semantically verify
  them.

### Risks and mitigations

- Risk: configuration becomes a generic bypass. Mitigation: use closed per-check declarations,
  explicit status, mandatory reasons, and normalized report evidence.
- Risk: configured paths escape or follow links. Mitigation: reject absolute, parent-relative,
  non-normalized, non-regular, and symlinked paths before reading.
- Risk: YAML consumes excessive resources. Mitigation: reuse the accepted byte, node-count, nesting,
  and safe-loading limits from ADR-0006.
- Risk: schema 1.0 consumers silently misread new output. Mitigation: advance the report schema to
  1.1 and preserve legacy input only where its meaning is unchanged.

## Alternatives considered

| Alternative | Evidence | Reason not selected |
|---|---|---|
| Recognize several conventional filenames | Portable project-contract naming has no sufficiently universal standard | Creates an arbitrary expanding filename list |
| Treat `disabled_checks` as the exception mechanism | Existing suppression removes the finding entirely | Hides status, reason, and evidence from the report |
| Infer authority from README or CI prose | S3NTINEL documents several commands but no single aggregate contract | Non-deterministic and likely to overclaim authority |
| Keep only `harness/project.yaml` | Existing implementation is simple and works for derived repositories | Contradicts general-purpose product scope and published remediation |

## Verification and revisit trigger

Verify configured-path, explicit-disposition, automatic-harness, absent, malformed, escaping,
directory, and symlink fixtures; repeated JSON and Markdown identity; complete target snapshots before
and after CLI execution; schema shape; and installed-package behavior.

Revisit if a portable project-contract standard becomes widely adopted, a downstream consumer needs
signed evidence provenance, or real usage shows that explicit dispositions require a separate policy
approval layer.
